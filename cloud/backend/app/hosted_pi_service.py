"""Provision and tear down cloud-hosted Pi sandboxes."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .event_status import normalize_status
from .hosted_pi_manager_client import HostedPiManagerError, destroy_instance, provision_instance
from .models import (
    Appliance,
    ApplianceEdgeCredential,
    ApplianceLending,
    Event,
    HostedPiInstance,
    Organisation,
)
from .security import get_password_hash

MAX_CONCURRENT_HOSTED_PI = 5
HOSTED_PI_TTL_HOURS = 24
ACTIVE_STATUSES = frozenset({"provisioning", "running", "stopping"})
HOSTED_PI_BASE_DOMAIN = os.getenv("HOSTED_PI_BASE_DOMAIN", "demo.vendiqo.ch")
CLOUD_BASE_URL = os.getenv("HOSTED_PI_CLOUD_BASE_URL", "https://api.vendiqo.ch").rstrip("/")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _public_url(slug: str) -> str:
    return f"https://{slug}.{HOSTED_PI_BASE_DOMAIN}"


def _active_instance_for_event(db: Session, event_id: int) -> HostedPiInstance | None:
    return (
        db.query(HostedPiInstance)
        .filter(
            HostedPiInstance.event_id == event_id,
            HostedPiInstance.status.in_(tuple(ACTIVE_STATUSES)),
        )
        .first()
    )


def _running_count(db: Session) -> int:
    return (
        db.query(HostedPiInstance)
        .filter(HostedPiInstance.status.in_(("provisioning", "running")))
        .count()
    )


def _generate_slug() -> str:
    return secrets.token_hex(6)


def hosted_pi_for_appliance(db: Session, appliance_id: int) -> HostedPiInstance | None:
    return (
        db.query(HostedPiInstance)
        .filter(
            HostedPiInstance.appliance_id == appliance_id,
            HostedPiInstance.status.in_(("provisioning", "running")),
        )
        .first()
    )


def instance_to_read(row: HostedPiInstance) -> dict:
    return {
        "id": row.id,
        "event_id": row.event_id,
        "status": row.status,
        "url": _public_url(row.subdomain_slug) if row.status in ("provisioning", "running") else None,
        "expires_at": row.expires_at,
        "created_at": row.created_at,
        "stopped_at": row.stopped_at,
        "last_error": row.last_error,
    }


async def create_hosted_pi(
    db: Session,
    *,
    event: Event,
    organisation: Organisation,
    hire_company_id: int,
    created_by_user_id: int | None,
) -> HostedPiInstance:
    if normalize_status(event.status) != "config":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hosted Pi is only available for events in config status",
        )
    if _active_instance_for_event(db, event.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A hosted Pi instance is already active for this event",
        )
    if _running_count(db) >= MAX_CONCURRENT_HOSTED_PI:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum of {MAX_CONCURRENT_HOSTED_PI} hosted Pi instances are already running",
        )

    slug = _generate_slug()
    now = _utc_now()
    expires_at = now + timedelta(hours=HOSTED_PI_TTL_HOURS)

    appliance = Appliance(
        hire_company_id=hire_company_id,
        type="server",
        name=f"Cloud-Pi {event.name}"[:255],
        is_hosted_virtual=True,
    )
    db.add(appliance)
    db.flush()

    today = now.date()
    db.add(
        ApplianceLending(
            appliance_id=appliance.id,
            organisation_id=organisation.id,
            start_date=today,
            end_date=today + timedelta(days=1),
        )
    )

    edge_secret = secrets.token_urlsafe(32)
    edge_credential = ApplianceEdgeCredential(
        appliance_id=appliance.id,
        label=f"hosted-{slug}",
        edge_client_id=uuid4().hex,
        edge_secret_hash=get_password_hash(edge_secret),
        status="active",
    )
    db.add(edge_credential)
    db.flush()

    instance = HostedPiInstance(
        event_id=event.id,
        organisation_id=organisation.id,
        hire_company_id=hire_company_id,
        appliance_id=appliance.id,
        edge_credential_id=edge_credential.id,
        subdomain_slug=slug,
        status="provisioning",
        created_by_user_id=created_by_user_id,
        expires_at=expires_at,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)

    try:
        await provision_instance(
            slug=slug,
            cloud_base_url=CLOUD_BASE_URL,
            edge_client_id=edge_credential.edge_client_id,
            edge_secret=edge_secret,
        )
        instance.status = "running"
        instance.last_error = None
        db.commit()
        db.refresh(instance)
    except HostedPiManagerError as exc:
        instance.status = "failed"
        instance.last_error = exc.detail[:2000]
        if edge_credential.status == "active":
            edge_credential.status = "revoked"
            edge_credential.revoked_at = _utc_now()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to start hosted Pi: {exc.detail}",
        ) from exc

    return instance


async def stop_hosted_pi(db: Session, instance: HostedPiInstance) -> HostedPiInstance:
    if instance.status in ("stopped", "failed"):
        return instance
    instance.status = "stopping"
    db.commit()

    if instance.edge_credential and instance.edge_credential.status == "active":
        instance.edge_credential.status = "revoked"
        instance.edge_credential.revoked_at = _utc_now()
    db.commit()

    try:
        await destroy_instance(instance.subdomain_slug)
    except HostedPiManagerError as exc:
        instance.last_error = exc.detail[:2000]

    instance.status = "stopped"
    instance.stopped_at = _utc_now()
    db.commit()
    db.refresh(instance)
    return instance


async def expire_due_instances(db: Session) -> int:
    now = _utc_now()
    rows = (
        db.query(HostedPiInstance)
        .filter(
            HostedPiInstance.status.in_(("provisioning", "running")),
            HostedPiInstance.expires_at <= now,
        )
        .all()
    )
    stopped = 0
    for row in rows:
        await stop_hosted_pi(db, row)
        stopped += 1
    return stopped


async def reconcile_stuck_provisioning(db: Session, *, timeout_minutes: int = 5) -> int:
    cutoff = _utc_now() - timedelta(minutes=timeout_minutes)
    rows = (
        db.query(HostedPiInstance)
        .filter(
            HostedPiInstance.status == "provisioning",
            HostedPiInstance.created_at <= cutoff,
        )
        .all()
    )
    failed = 0
    for row in rows:
        row.status = "failed"
        row.last_error = row.last_error or "Provisioning timed out"
        row.stopped_at = _utc_now()
        if row.edge_credential and row.edge_credential.status == "active":
            row.edge_credential.status = "revoked"
            row.edge_credential.revoked_at = _utc_now()
        try:
            await destroy_instance(row.subdomain_slug)
        except HostedPiManagerError:
            pass
        failed += 1
    if failed:
        db.commit()
    return failed
