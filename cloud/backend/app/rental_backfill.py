"""Backfill one rental per legacy appliance lending (null rental_id)."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection


def backfill_appliance_lending_rentals(conn: Connection) -> int:
    """Create a rental for each lending that has no rental_id. Returns updated lending count."""
    rows = conn.execute(
        text(
            """
            SELECT al.id AS lending_id,
                   al.organisation_id,
                   al.start_date,
                   al.end_date,
                   o.hire_company_id
            FROM appliance_lendings al
            JOIN organisations o ON o.id = al.organisation_id
            WHERE al.rental_id IS NULL
            ORDER BY al.id
            """
        )
    ).fetchall()
    updated = 0
    is_sqlite = conn.dialect.name == "sqlite"
    for row in rows:
        params = {
            "hid": row.hire_company_id,
            "oid": row.organisation_id,
            "start": row.start_date,
            "end": row.end_date,
        }
        if is_sqlite:
            conn.execute(
                text(
                    """
                    INSERT INTO rentals (hire_company_id, organisation_id, start_date, end_date, label)
                    VALUES (:hid, :oid, :start, :end, NULL)
                    """
                ),
                params,
            )
            rental_id = conn.execute(text("SELECT last_insert_rowid()")).scalar()
        else:
            rental_id = conn.execute(
                text(
                    """
                    INSERT INTO rentals (hire_company_id, organisation_id, start_date, end_date, label)
                    VALUES (:hid, :oid, :start, :end, NULL)
                    RETURNING id
                    """
                ),
                params,
            ).scalar()
        conn.execute(
            text("UPDATE appliance_lendings SET rental_id = :rid WHERE id = :lid"),
            {"rid": rental_id, "lid": row.lending_id},
        )
        updated += 1
    return updated
