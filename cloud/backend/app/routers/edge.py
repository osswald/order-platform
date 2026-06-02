"""Device-authenticated API for on-prem Raspberry Pi (server appliance)."""

import re
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from ..models import (
    Appliance,
    ApplianceEdgeCredential,
    ApplianceLending,
    AppliancePairingSession,
    EdgeSubmittedOrder,
    EdgeOrderItem,
    EdgePayment,
    EdgePaymentBatch,
    EdgeOrderSession,
    Event,
    EventAppLayout,
    EventAppLayoutCell,
    EventCashRegister,
    EventStation,
    User,
    organisation_users,
)
from ..payment_types_config import payment_types_from_event
from ..twint_qr import twint_qr_data_url_for_event
from ..event_status import ORDER_ACCEPT_STATUSES, PI_VISIBLE_STATUSES
from ..stock import apply_stock_deductions, article_snapshot_for_event
from ..security import get_password_hash, verify_password
from ..deps import get_db
from ..rate_limit import EDGE_PAIR_RATE_LIMIT, limiter
from .events import serialize_event_configuration

router = APIRouter()
PAIRING_CODE_PATTERN = re.compile(r"\D+")


def _utc_today():
    return datetime.now(timezone.utc).date()


class ApplianceEdgeContext:
    def __init__(
        self,
        appliance: Appliance,
        organisation_id: int,
        edge_credential: ApplianceEdgeCredential | None = None,
    ):
        self.appliance = appliance
        self.organisation_id = organisation_id
        self.edge_credential = edge_credential


def get_edge_server_appliance(
    db: Session = Depends(get_db),
    x_edge_client_id: str | None = Header(None, alias="X-Edge-Client-Id"),
    x_edge_secret: str | None = Header(None, alias="X-Edge-Secret"),
) -> ApplianceEdgeContext:
    if not x_edge_client_id or not x_edge_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Edge-Client-Id or X-Edge-Secret",
        )
    edge_credential = (
        db.query(ApplianceEdgeCredential)
        .join(Appliance, Appliance.id == ApplianceEdgeCredential.appliance_id)
        .filter(
            ApplianceEdgeCredential.edge_client_id == x_edge_client_id,
            ApplianceEdgeCredential.status == "active",
            ApplianceEdgeCredential.revoked_at.is_(None),
            Appliance.type == "server",
        )
        .first()
    )
    if edge_credential is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device")
    appliance = edge_credential.appliance
    if not verify_password(x_edge_secret, edge_credential.edge_secret_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials")

    today = _utc_today()
    lending = (
        db.query(ApplianceLending)
        .options(joinedload(ApplianceLending.organisation))
        .filter(
            ApplianceLending.appliance_id == appliance.id,
            ApplianceLending.returned_at.is_(None),
            ApplianceLending.start_date <= today,
            ApplianceLending.end_date >= today,
        )
        .first()
    )
    if not lending:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active appliance lending for this device today",
        )
    org = lending.organisation
    if not org or org.hire_company_id != appliance.hire_company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lending organisation does not match appliance Verleiher",
        )
    if edge_credential is not None:
        edge_credential.last_seen_at = datetime.now(timezone.utc)
        db.commit()
    return ApplianceEdgeContext(appliance, lending.organisation_id, edge_credential=edge_credential)


def _load_event_for_org(db: Session, event_id: int, organisation_id: int) -> Event | None:
    return (
        db.query(Event)
        .options(
            joinedload(Event.organisation),
            joinedload(Event.stations).joinedload(EventStation.articles),
            joinedload(Event.event_waiters),
            joinedload(Event.app_layouts).joinedload(EventAppLayout.cells).joinedload(EventAppLayoutCell.articles),
            joinedload(Event.cash_registers),
            joinedload(Event.voucher_definitions),
        )
        .filter(Event.id == event_id, Event.organisation_id == organisation_id)
        .first()
    )


def _active_events_for_org(db: Session, organisation_id: int) -> list[Event]:
    now = datetime.now(timezone.utc)
    return (
        db.query(Event)
        .options(
            joinedload(Event.organisation),
            joinedload(Event.stations).joinedload(EventStation.articles),
            joinedload(Event.event_waiters),
            joinedload(Event.app_layouts).joinedload(EventAppLayout.cells).joinedload(EventAppLayoutCell.articles),
            joinedload(Event.cash_registers),
            joinedload(Event.voucher_definitions),
        )
        .filter(
            Event.organisation_id == organisation_id,
            Event.status.in_(tuple(PI_VISIBLE_STATUSES)),
            Event.start <= now,
            Event.end >= now,
        )
        .order_by(Event.start.asc())
        .all()
    )


def _article_snapshot(db: Session, event: Event) -> dict[str, Any]:
    return article_snapshot_for_event(db, event)


def _printer_hosts_by_station(db: Session, event: Event) -> dict[str, dict]:
    """Map station/register uuid -> ESC/POS endpoint (host, port, feed_lines from printer appliance)."""
    from ..printer_appliance_config import PrinterHostEndpoint, feed_lines_for_appliance

    out: dict[str, dict] = {}

    def add_endpoint(key: str, ap: Appliance | None) -> None:
        if not ap or not ap.ip_address:
            return
        endpoint = PrinterHostEndpoint(
            host=ap.ip_address.strip(),
            port=9100,
            feed_lines=feed_lines_for_appliance(ap),
        )
        out[key] = endpoint.model_dump()

    for st in event.stations or []:
        if not st.printer_appliance_id:
            continue
        ap = db.query(Appliance).filter(Appliance.id == st.printer_appliance_id).first()
        add_endpoint(str(st.uuid), ap)
    for reg in event.cash_registers or []:
        if not reg.receipt_printer_appliance_id:
            continue
        ap = db.query(Appliance).filter(Appliance.id == reg.receipt_printer_appliance_id).first()
        add_endpoint(str(reg.uuid), ap)
    return out


class EdgeEventBundle(BaseModel):
    id: int
    name: str
    status: str
    currency: str
    payment_mode: str
    payment_types: list[str] = Field(default_factory=lambda: ["cash"])
    twint_qr_data_url: str | None = None
    start: datetime
    end: datetime
    configuration: dict[str, Any]
    articles: dict[str, Any]
    printer_hosts: dict[str, dict] = Field(default_factory=dict)


class EdgeBundleRead(BaseModel):
    organisation_id: int
    appliance_id: int
    server_time: datetime
    events: list[EdgeEventBundle]
    admin_pin_hashes: list[str] = Field(default_factory=list)


class EdgePairRequest(BaseModel):
    pairing_code: str = Field(..., min_length=6, max_length=32)
    device_name: str | None = Field(None, max_length=255)


class EdgePairResponse(BaseModel):
    appliance_id: int
    appliance_name: str | None = None
    edge_credential_id: int
    installation_label: str | None = None
    edge_client_id: str
    edge_secret: str


def _normalize_pairing_code(code: str) -> str:
    return PAIRING_CODE_PATTERN.sub("", code or "")


@router.post("/v1/pair", response_model=EdgePairResponse)
@limiter.limit(EDGE_PAIR_RATE_LIMIT)
def pair_edge_device(request: Request, body: EdgePairRequest, db: Session = Depends(get_db)):
    code = _normalize_pairing_code(body.pairing_code)
    if len(code) != 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Pairing code must have 6 digits")

    now = datetime.now(timezone.utc)
    sessions = (
        db.query(AppliancePairingSession)
        .join(Appliance, Appliance.id == AppliancePairingSession.appliance_id)
        .filter(
            Appliance.type == "server",
            AppliancePairingSession.consumed_at.is_(None),
            AppliancePairingSession.expires_at > now,
        )
        .all()
    )
    matched = next((session for session in sessions if verify_password(code, session.code_hash)), None)
    if matched is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired pairing code")

    appliance = matched.appliance
    secret = secrets.token_urlsafe(32)
    label = (body.device_name or "").strip() or None
    edge_credential = ApplianceEdgeCredential(
        appliance_id=appliance.id,
        label=label,
        edge_client_id=uuid4().hex,
        edge_secret_hash=get_password_hash(secret),
        status="active",
    )
    db.add(edge_credential)
    matched.consumed_at = now
    db.commit()
    db.refresh(edge_credential)
    return EdgePairResponse(
        appliance_id=appliance.id,
        appliance_name=appliance.name,
        edge_credential_id=edge_credential.id,
        installation_label=edge_credential.label,
        edge_client_id=edge_credential.edge_client_id,
        edge_secret=secret,
    )


def _admin_pin_hashes_for_org(db: Session, organisation_id: int) -> list[str]:
    rows = (
        db.query(User.event_admin_pin_hash)
        .join(organisation_users, organisation_users.c.user_id == User.id)
        .filter(
            organisation_users.c.organisation_id == organisation_id,
            User.is_active.is_(True),
            User.event_admin_pin_hash.isnot(None),
        )
        .distinct()
        .all()
    )
    return [h for (h,) in rows if h]


@router.get("/v1/bundle", response_model=EdgeBundleRead)
def read_edge_bundle(
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
):
    appliance = ctx.appliance
    org_id = ctx.organisation_id
    events = _active_events_for_org(db, org_id)
    bundles: list[EdgeEventBundle] = []
    for ev in events:
        cfg = serialize_event_configuration(db, ev)
        cfg_dict = cfg.model_dump() if hasattr(cfg, "model_dump") else cfg.dict()
        from ..receipt_printing_config import printing_bundle_dict

        cfg_dict["printing"] = printing_bundle_dict(ev)
        bundles.append(
            EdgeEventBundle(
                id=ev.id,
                name=ev.name,
                status=(ev.status or "config").lower(),
                currency=ev.currency,
                payment_mode=getattr(ev, "payment_mode", None) or "pay_later",
                payment_types=payment_types_from_event(ev),
                twint_qr_data_url=twint_qr_data_url_for_event(ev),
                start=ev.start,
                end=ev.end,
                configuration=cfg_dict,
                articles=_article_snapshot(db, ev),
                printer_hosts=_printer_hosts_by_station(db, ev),
            )
        )
    db.commit()
    return EdgeBundleRead(
        organisation_id=org_id,
        appliance_id=appliance.id,
        server_time=datetime.now(timezone.utc),
        events=bundles,
        admin_pin_hashes=_admin_pin_hashes_for_org(db, org_id),
    )


class EdgeOrderCreate(BaseModel):
    client_order_id: str = Field(..., min_length=8, max_length=64)
    event_id: int
    payload: dict[str, Any] = Field(default_factory=dict)


class EdgeOrderAck(BaseModel):
    server_order_id: int
    duplicate: bool = False


class EdgeOperationalChunkCreate(BaseModel):
    chunk_id: str = Field(..., min_length=8, max_length=64)
    event_id: int
    entity_type: str = Field(..., min_length=1, max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)


class EdgeOperationalChunkAck(BaseModel):
    chunk_id: str
    status: str = "acked"
    accepted: int = 1


class EdgeUnpairAck(BaseModel):
    status: str = "revoked"


@router.post("/v1/unpair", response_model=EdgeUnpairAck)
def unpair_edge_device(
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
):
    credential = ctx.edge_credential
    if credential is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device")
    if credential.status != "revoked" or credential.revoked_at is None:
        credential.status = "revoked"
        credential.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return EdgeUnpairAck(status="revoked")


@router.post("/v1/orders", response_model=EdgeOrderAck)
def submit_edge_order(
    body: EdgeOrderCreate,
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
):
    existing = db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.client_order_id == body.client_order_id).first()
    if existing:
        return EdgeOrderAck(server_order_id=existing.id, duplicate=True)

    event = _load_event_for_org(db, body.event_id, ctx.organisation_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found for organisation")

    ev_status = (event.status or "config").lower()
    if ev_status not in ORDER_ACCEPT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Event status {ev_status} does not accept orders",
        )

    lines = (body.payload or {}).get("lines") or []
    stock_lines = [
        ln for ln in lines if isinstance(ln, dict) and str(ln.get("kind") or "") != "voucher_sale"
    ]
    if stock_lines:
        from ..models import Article

        names: dict[int, str] = {}
        for st in event.stations or []:
            for a in st.articles or []:
                names[a.id] = a.name
        extra_ids: set[int] = set()
        for line in lines:
            for add in line.get("additions") or []:
                if isinstance(add, dict) and add.get("article_id") is not None:
                    extra_ids.add(int(add["article_id"]))
        if extra_ids:
            for a in db.query(Article).filter(Article.id.in_(list(extra_ids))).all():
                names[a.id] = a.name
        apply_stock_deductions(db, event.id, stock_lines, article_names=names)

    from ..event_collective_bills import upsert_collective_bill_from_payload

    payload = body.payload or {}
    upsert_collective_bill_from_payload(
        db,
        event_id=body.event_id,
        appliance_id=ctx.appliance.id,
        payload=payload,
    )

    from ..vouchers import persist_voucher_redemptions_from_payload

    pay_cid = str(payload.get("client_order_id") or body.client_order_id)
    persist_voucher_redemptions_from_payload(
        db,
        event_id=body.event_id,
        payment_client_order_id=pay_cid,
        redemptions=payload.get("voucher_redemptions") or [],
    )

    row = EdgeSubmittedOrder(
        client_order_id=body.client_order_id,
        appliance_id=ctx.appliance.id,
        organisation_id=ctx.organisation_id,
        event_id=body.event_id,
        payload=payload,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return EdgeOrderAck(server_order_id=row.id, duplicate=False)


@router.post("/v1/sync/operational/chunk", response_model=EdgeOperationalChunkAck)
def submit_operational_chunk(
    body: EdgeOperationalChunkCreate,
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
):
    event = _load_event_for_org(db, body.event_id, ctx.organisation_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found for organisation")

    payload = body.payload or {}
    existing = (
        db.query(EdgeSubmittedOrder)
        .filter(EdgeSubmittedOrder.client_order_id == body.chunk_id)
        .first()
    )
    if existing:
        return EdgeOperationalChunkAck(chunk_id=body.chunk_id, status="acked", accepted=0)

    # Keep audit trail while migrating.
    db.add(
        EdgeSubmittedOrder(
            client_order_id=body.chunk_id,
            appliance_id=ctx.appliance.id,
            organisation_id=ctx.organisation_id,
            event_id=body.event_id,
            payload={"entity_type": body.entity_type, **payload},
        )
    )

    lines = payload.get("lines") or []
    payments = payload.get("payments") or []
    submission_id = int(payload.get("submission_id") or payload.get("local_order_id") or 0) or None
    session_id = int(payload.get("session_id") or 0) or submission_id or 0
    table_number = payload.get("table_number")
    waiter_uuid = payload.get("waiter_uuid")
    payment_status = str(payload.get("payment_status") or "open")
    method = str(payments[0].get("type") if payments and isinstance(payments[0], dict) else "cash")
    batch_uuid = str(payload.get("collective_bill_uuid") or "")

    if session_id:
        db.add(
            EdgeOrderSession(
                organisation_id=ctx.organisation_id,
                appliance_id=ctx.appliance.id,
                event_id=body.event_id,
                session_id=session_id,
                table_number=table_number,
                order_source=str(payload.get("order_source") or "waiter"),
            )
        )
    line_sum = 0
    for line in lines:
        if not isinstance(line, dict):
            continue
        qty = int(line.get("qty") or 1)
        unit = int(line.get("unit_cents") or line.get("unit_price_cents") or 0)
        lc = max(0, qty * unit)
        line_sum += lc
        db.add(
            EdgeOrderItem(
                organisation_id=ctx.organisation_id,
                appliance_id=ctx.appliance.id,
                event_id=body.event_id,
                session_id=session_id,
                submission_id=submission_id,
                article_id=int(line["article_id"]) if line.get("article_id") is not None else None,
                article_name=str(line.get("article_name") or ""),
                station_uuid=line.get("station_uuid"),
                waiter_uuid=waiter_uuid,
                quantity=qty,
                unit_price_cents=unit,
                line_total_cents=lc,
                payment_status=payment_status,
                payment_batch_uuid=batch_uuid or None,
                method=method,
                payload=line,
            )
        )
    if batch_uuid:
        db.add(
            EdgePaymentBatch(
                organisation_id=ctx.organisation_id,
                appliance_id=ctx.appliance.id,
                event_id=body.event_id,
                batch_uuid=batch_uuid,
                name=str(payload.get("collective_bill_name") or "Sammelrechnung"),
                status="closed" if payment_status == "paid" else "open",
                total_cents=line_sum,
            )
        )
    if payment_status == "paid":
        for p in payments:
            if not isinstance(p, dict):
                continue
            db.add(
                EdgePayment(
                    organisation_id=ctx.organisation_id,
                    appliance_id=ctx.appliance.id,
                    event_id=body.event_id,
                    submission_id=submission_id,
                    payment_batch_uuid=batch_uuid or None,
                    method=str(p.get("type") or "cash"),
                    amount_cents=int(p.get("amount_cents") or 0),
                    payload=p,
                )
            )
    db.commit()
    return EdgeOperationalChunkAck(chunk_id=body.chunk_id, status="acked", accepted=1)
