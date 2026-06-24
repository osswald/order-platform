"""Device-authenticated API for on-prem Raspberry Pi (server appliance)."""

import re
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Query, Request, status
from ..i18n.errors import api_error
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..currency import event_currency
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
    Organisation,
    OrganisationPositionComment,
    User,
    organisation_users,
)
from ..payment_types_config import payment_types_from_event
from ..twint_qr import twint_qr_data_url_for_event
from ..event_status import ORDER_ACCEPT_STATUSES, PI_VISIBLE_STATUSES, normalize_status
from ..stock import apply_stock_deductions, article_snapshot_for_event
from ..security import get_password_hash, verify_password
from ..deps import get_db
from ..event_cash_sessions import upsert_edge_cash_session
from ..edge_operational_mirror import (
    upsert_edge_kitchen_ticket_snapshot,
    upsert_edge_order_snapshot,
)
from ..edge_operational_snapshot import build_operational_snapshot_for_events
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
        raise api_error("missing_edge_headers", status.HTTP_401_UNAUTHORIZED)
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
        raise api_error("invalid_device", status.HTTP_401_UNAUTHORIZED)
    appliance = edge_credential.appliance
    if not verify_password(x_edge_secret, edge_credential.edge_secret_hash):
        raise api_error("invalid_device_credentials", status.HTTP_401_UNAUTHORIZED)

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
        raise api_error("no_active_lending_today", status.HTTP_403_FORBIDDEN)
    org = lending.organisation
    if not org or org.hire_company_id != appliance.hire_company_id:
        raise api_error("lending_org_mismatch", status.HTTP_403_FORBIDDEN)
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
            joinedload(Event.kitchen_monitor_printers),
            joinedload(Event.stations).joinedload(EventStation.printer_rules),
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
            joinedload(Event.kitchen_monitor_printers),
            joinedload(Event.stations).joinedload(EventStation.printer_rules),
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


def _emulated_printer_hosts(event: Event) -> dict[str, dict]:
    out: dict[str, dict] = {}
    appliance_ids: set[int] = set()
    for st in event.stations or []:
        out[str(st.uuid)] = {"host": "emulated", "port": 0, "feed_lines": 1}
        if st.printer_appliance_id:
            appliance_ids.add(int(st.printer_appliance_id))
        for rule in st.printer_rules or []:
            if rule.printer_appliance_id:
                appliance_ids.add(int(rule.printer_appliance_id))
    for reg in event.cash_registers or []:
        out[str(reg.uuid)] = {"host": "emulated", "port": 0, "feed_lines": 1}
        if reg.receipt_printer_appliance_id:
            appliance_ids.add(int(reg.receipt_printer_appliance_id))
    for row in event.kitchen_monitor_printers or []:
        appliance_ids.add(int(row.printer_appliance_id))
    for aid in appliance_ids:
        out[f"appliance:{aid}"] = {"host": "emulated", "port": 0, "feed_lines": 1}
    return out


def _load_event_bundle_row(db: Session, event_id: int, organisation_id: int) -> Event | None:
    return (
        db.query(Event)
        .options(
            joinedload(Event.organisation),
            joinedload(Event.stations).joinedload(EventStation.articles),
            joinedload(Event.event_waiters),
            joinedload(Event.app_layouts).joinedload(EventAppLayout.cells).joinedload(EventAppLayoutCell.articles),
            joinedload(Event.cash_registers),
            joinedload(Event.voucher_definitions),
            joinedload(Event.kitchen_monitor_printers),
            joinedload(Event.stations).joinedload(EventStation.printer_rules),
        )
        .filter(Event.id == event_id, Event.organisation_id == organisation_id)
        .first()
    )


def _events_for_edge_bundle(db: Session, ctx: ApplianceEdgeContext) -> tuple[list[Event], bool]:
    """Return events for bundle pull and whether printer hosts should be emulated."""
    from ..hosted_pi_service import hosted_pi_for_appliance

    hosted = hosted_pi_for_appliance(db, ctx.appliance.id)
    if hosted and getattr(ctx.appliance, "is_hosted_virtual", False):
        event = _load_event_bundle_row(db, hosted.event_id, ctx.organisation_id)
        if event and normalize_status(event.status) == "config":
            return [event], True
        return [], True
    return _active_events_for_org(db, ctx.organisation_id), False


def _article_snapshot(db: Session, event: Event) -> dict[str, Any]:
    return article_snapshot_for_event(db, event)


def _printer_hosts_by_station(db: Session, event: Event) -> dict[str, dict]:
    """Map station/register/appliance keys -> ESC/POS endpoint (host, port, feed_lines)."""
    from ..printer_appliance_config import PrinterHostEndpoint, feed_lines_for_appliance

    out: dict[str, dict] = {}
    appliance_ids: set[int] = set()

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
        if st.printer_appliance_id:
            appliance_ids.add(int(st.printer_appliance_id))
        for rule in st.printer_rules or []:
            if rule.printer_appliance_id:
                appliance_ids.add(int(rule.printer_appliance_id))
        if not st.printer_appliance_id:
            continue
        ap = db.query(Appliance).filter(Appliance.id == st.printer_appliance_id).first()
        add_endpoint(str(st.uuid), ap)
    for reg in event.cash_registers or []:
        if reg.receipt_printer_appliance_id:
            appliance_ids.add(int(reg.receipt_printer_appliance_id))
        if not reg.receipt_printer_appliance_id:
            continue
        ap = db.query(Appliance).filter(Appliance.id == reg.receipt_printer_appliance_id).first()
        add_endpoint(str(reg.uuid), ap)
    for row in event.kitchen_monitor_printers or []:
        appliance_ids.add(int(row.printer_appliance_id))
    for aid in sorted(appliance_ids):
        ap = db.query(Appliance).filter(Appliance.id == aid).first()
        add_endpoint(f"appliance:{aid}", ap)
    return out


class EdgeEventBundle(BaseModel):
    id: int
    name: str
    status: str
    currency: str
    payment_mode: str
    payment_types: list[str] = Field(default_factory=lambda: ["cash"])
    instant_collective_bill_name: str | None = None
    instant_collective_bill_uuid: str | None = None
    shift_settlement_enabled: bool = False
    discounts_enabled: bool = False
    alternative_printers_enabled: bool = False
    kitchen_monitors_enabled: bool = False
    offer_payment_receipt: bool = False
    twint_qr_data_url: str | None = None
    start: datetime
    end: datetime
    configuration: dict[str, Any]
    articles: dict[str, Any]
    printer_hosts: dict[str, dict] = Field(default_factory=dict)


class PositionCommentPresetBundleRead(BaseModel):
    id: int
    text: str


class EdgeBundleRead(BaseModel):
    organisation_id: int
    appliance_id: int
    server_time: datetime
    events: list[EdgeEventBundle]
    admin_pin_hashes: list[str] = Field(default_factory=list)
    position_comments_enabled: bool = False
    position_comment_presets: list[PositionCommentPresetBundleRead] = Field(default_factory=list)


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
        raise api_error("pairing_code_must_6_digits", status.HTTP_422_UNPROCESSABLE_CONTENT)

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
        raise api_error("invalid_or_expired_pairing_code", status.HTTP_401_UNAUTHORIZED)

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


def _position_comment_presets_for_org(db: Session, organisation_id: int) -> list[dict]:
    rows = (
        db.query(OrganisationPositionComment)
        .filter(OrganisationPositionComment.organisation_id == organisation_id)
        .order_by(OrganisationPositionComment.sort_order, OrganisationPositionComment.id)
        .all()
    )
    return [{"id": row.id, "text": row.text} for row in rows]


@router.get("/v1/bundle", response_model=EdgeBundleRead)
def read_edge_bundle(
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
):
    appliance = ctx.appliance
    org_id = ctx.organisation_id
    events, emulated_printers = _events_for_edge_bundle(db, ctx)
    bundles: list[EdgeEventBundle] = []
    for ev in events:
        cfg = serialize_event_configuration(db, ev)
        cfg_dict = cfg.model_dump() if hasattr(cfg, "model_dump") else cfg.dict()
        from ..receipt_printing_config import printing_bundle_dict

        cfg_dict["printing"] = printing_bundle_dict(ev)
        printer_hosts = _emulated_printer_hosts(ev) if emulated_printers else _printer_hosts_by_station(db, ev)
        bundles.append(
            EdgeEventBundle(
                id=ev.id,
                name=ev.name,
                status=(ev.status or "config").lower(),
                currency=event_currency(ev, "CHF"),
                payment_mode=getattr(ev, "payment_mode", None) or "pay_later",
                payment_types=payment_types_from_event(ev),
                instant_collective_bill_name=getattr(ev, "instant_collective_bill_name", None),
                instant_collective_bill_uuid=getattr(ev, "instant_collective_bill_uuid", None),
                shift_settlement_enabled=bool(getattr(ev, "shift_settlement_enabled", False)),
                discounts_enabled=bool(getattr(ev, "discounts_enabled", False)),
                alternative_printers_enabled=bool(getattr(ev, "alternative_printers_enabled", False)),
                kitchen_monitors_enabled=bool(getattr(ev, "kitchen_monitors_enabled", False)),
                offer_payment_receipt=bool(getattr(ev, "offer_payment_receipt", False)),
                twint_qr_data_url=twint_qr_data_url_for_event(ev),
                start=ev.start,
                end=ev.end,
                configuration=cfg_dict,
                articles=_article_snapshot(db, ev),
                printer_hosts=printer_hosts,
            )
        )
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    position_comments_enabled = bool(org and org.position_comments_enabled)
    position_comment_presets = (
        _position_comment_presets_for_org(db, org_id) if position_comments_enabled else []
    )
    db.commit()
    return EdgeBundleRead(
        organisation_id=org_id,
        appliance_id=appliance.id,
        server_time=datetime.now(timezone.utc),
        events=bundles,
        admin_pin_hashes=_admin_pin_hashes_for_org(db, org_id),
        position_comments_enabled=position_comments_enabled,
        position_comment_presets=position_comment_presets,
    )


@router.get("/v1/sync/operational/snapshot")
def read_operational_snapshot(
    event_id: int | None = Query(None),
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
):
    """Org/event operational state for Pi restore (cross-appliance takeover)."""
    events, _emulated = _events_for_edge_bundle(db, ctx)
    if event_id is not None:
        events = [ev for ev in events if int(ev.id) == int(event_id)]
    snapshot = build_operational_snapshot_for_events(
        db,
        organisation_id=ctx.organisation_id,
        events=events,
    )
    snapshot["appliance_id"] = ctx.appliance.id
    snapshot["server_time"] = datetime.now(timezone.utc)
    return snapshot


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
        raise api_error("invalid_device", status.HTTP_401_UNAUTHORIZED)
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
    event = _load_event_for_org(db, body.event_id, ctx.organisation_id)
    if not event:
        raise api_error("event_not_found_for_organisation", status.HTTP_404_NOT_FOUND)

    ev_status = (event.status or "config").lower()
    if ev_status not in ORDER_ACCEPT_STATUSES:
        raise api_error("event_status_does_not_accept_orders", status.HTTP_403_FORBIDDEN, status=ev_status)

    payload = body.payload or {}
    row = EdgeSubmittedOrder(
        client_order_id=body.client_order_id,
        appliance_id=ctx.appliance.id,
        organisation_id=ctx.organisation_id,
        event_id=body.event_id,
        payload=payload,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(EdgeSubmittedOrder)
            .filter(EdgeSubmittedOrder.client_order_id == body.client_order_id)
            .first()
        )
        if existing is None:
            raise
        return EdgeOrderAck(server_order_id=existing.id, duplicate=True)

    lines = payload.get("lines") or []
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

    upsert_edge_order_snapshot(
        db,
        organisation_id=ctx.organisation_id,
        appliance_id=ctx.appliance.id,
        event_id=body.event_id,
        payload=payload,
    )
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
        raise api_error("event_not_found_for_organisation", status.HTTP_404_NOT_FOUND)

    payload = body.payload or {}
    entity_type = (body.entity_type or payload.get("entity_type") or "").strip().lower()
    existing = (
        db.query(EdgeSubmittedOrder)
        .filter(EdgeSubmittedOrder.client_order_id == body.chunk_id)
        .first()
    )
    if existing:
        return EdgeOperationalChunkAck(chunk_id=body.chunk_id, status="acked", accepted=0)

    if entity_type == "cash_session":
        upsert_edge_cash_session(
            db,
            organisation_id=ctx.organisation_id,
            appliance_id=ctx.appliance.id,
            event_id=body.event_id,
            payload=payload,
        )
        db.commit()
        return EdgeOperationalChunkAck(chunk_id=body.chunk_id, status="acked", accepted=1)

    if entity_type == "kitchen_tickets":
        db.add(
            EdgeSubmittedOrder(
                client_order_id=body.chunk_id,
                appliance_id=ctx.appliance.id,
                organisation_id=ctx.organisation_id,
                event_id=body.event_id,
                payload={"entity_type": body.entity_type, **payload},
            )
        )
        upsert_edge_kitchen_ticket_snapshot(
            db,
            organisation_id=ctx.organisation_id,
            appliance_id=ctx.appliance.id,
            event_id=body.event_id,
            payload=payload,
        )
        db.commit()
        return EdgeOperationalChunkAck(chunk_id=body.chunk_id, status="acked", accepted=1)

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
    cash_register_uuid = payload.get("cash_register_uuid")
    order_source = str(payload.get("order_source") or "waiter")
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
        gross = int(line.get("gross_cents") if line.get("gross_cents") is not None else max(0, qty * unit))
        line_sum += gross
        tax_code_id = int(line["tax_code_id"]) if line.get("tax_code_id") is not None else None
        accounting_account_id = (
            int(line["accounting_account_id"]) if line.get("accounting_account_id") is not None else None
        )
        tax_rate = float(line["tax_rate_percent"]) if line.get("tax_rate_percent") is not None else None
        net_cents = int(line["net_cents"]) if line.get("net_cents") is not None else None
        vat_cents = int(line["vat_cents"]) if line.get("vat_cents") is not None else None
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
                cash_register_uuid=cash_register_uuid,
                order_source=order_source,
                quantity=qty,
                unit_price_cents=unit,
                line_total_cents=gross,
                tax_code_id=tax_code_id,
                tax_rate_percent=tax_rate,
                accounting_account_id=accounting_account_id,
                net_cents=net_cents,
                vat_cents=vat_cents,
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
    upsert_edge_order_snapshot(
        db,
        organisation_id=ctx.organisation_id,
        appliance_id=ctx.appliance.id,
        event_id=body.event_id,
        payload=payload,
    )
    db.commit()
    return EdgeOperationalChunkAck(chunk_id=body.chunk_id, status="acked", accepted=1)
