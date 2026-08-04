"""Add cash_session_uuid; history unique by session instance

Revision ID: 009_cash_session_uuid
Revises: 008_edge_credential_reported_app_version
Create Date: 2026-07-31
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_cash_session_uuid"
down_revision: Union[str, Sequence[str], None] = "008_edge_credential_reported_app_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "edge_cash_sessions" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("edge_cash_sessions")}
    if "cash_session_uuid" not in cols:
        op.add_column(
            "edge_cash_sessions",
            sa.Column("cash_session_uuid", sa.String(length=36), nullable=True),
        )

    rows = bind.execute(
        sa.text("SELECT id FROM edge_cash_sessions WHERE cash_session_uuid IS NULL")
    ).fetchall()
    for (row_id,) in rows:
        bind.execute(
            sa.text("UPDATE edge_cash_sessions SET cash_session_uuid = :u WHERE id = :id"),
            {"u": str(uuid.uuid4()), "id": row_id},
        )

    op.alter_column(
        "edge_cash_sessions",
        "cash_session_uuid",
        existing_type=sa.String(length=36),
        nullable=False,
    )

    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("edge_cash_sessions")}
    if "ix_edge_cash_sessions_org_event_subject" in indexes:
        op.drop_index("ix_edge_cash_sessions_org_event_subject", table_name="edge_cash_sessions")

    if "ix_edge_cash_sessions_org_event_uuid" not in indexes:
        op.create_index(
            "ix_edge_cash_sessions_org_event_uuid",
            "edge_cash_sessions",
            ["organisation_id", "event_id", "cash_session_uuid"],
            unique=True,
        )
    if "ix_edge_cash_sessions_cash_session_uuid" not in indexes:
        op.create_index(
            "ix_edge_cash_sessions_cash_session_uuid",
            "edge_cash_sessions",
            ["cash_session_uuid"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "edge_cash_sessions" not in inspector.get_table_names():
        return
    indexes = {idx["name"] for idx in inspector.get_indexes("edge_cash_sessions")}
    if "ix_edge_cash_sessions_org_event_uuid" in indexes:
        op.drop_index("ix_edge_cash_sessions_org_event_uuid", table_name="edge_cash_sessions")
    if "ix_edge_cash_sessions_cash_session_uuid" in indexes:
        op.drop_index("ix_edge_cash_sessions_cash_session_uuid", table_name="edge_cash_sessions")
    if "ix_edge_cash_sessions_org_event_subject" not in indexes:
        op.create_index(
            "ix_edge_cash_sessions_org_event_subject",
            "edge_cash_sessions",
            ["organisation_id", "event_id", "subject_key"],
            unique=True,
        )
    cols = {c["name"] for c in inspector.get_columns("edge_cash_sessions")}
    if "cash_session_uuid" in cols:
        op.drop_column("edge_cash_sessions", "cash_session_uuid")
