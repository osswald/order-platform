"""Edge API router — admin, printers, print jobs, and sub-router wiring."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..bundle_cache import event_from_bundle, get_bundle_dict
from ..deps import get_db
from ..models import EmulatedReceipt, LocalOrder, PrintJob, SyncedBundle
from ..print_worker import (
    build_escpos_station_test_slip,
    build_payment_receipt_text,
    station_name_from_event,
    _send_to_printer,
)
from ..printer_endpoint import resolve_printer_endpoint
from ..schemas.edge import (
    AdminStatusResponse,
    AdminVerifyBody,
    EscposPayloadResponse,
    OkResponse,
    PrintJobRetryResponse,
    PrintJobSummary,
    PrinterTestReceiptBody,
    PrinterTestStationPrintsBody,
    PrinterTestStationPrintsResponse,
    StationTestPrintResult,
)
from ..security import verify_password
from .edge_common import _article_map

router = APIRouter()


def _bundle_dict_optional(db: Session) -> dict | None:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row or not row.json_body:
        return None
    data = json.loads(row.json_body)
    if not isinstance(data, dict) or data.get("organisation_id") is None:
        return None
    return data


@router.get("/v1/admin/status", response_model=AdminStatusResponse)
def admin_status(db: Session = Depends(get_db)) -> AdminStatusResponse:
    bundle = _bundle_dict_optional(db)
    bundle_ready = bundle is not None
    hashes = (bundle or {}).get("admin_pin_hashes") or []
    return AdminStatusResponse(
        bundle_ready=bundle_ready,
        requires_pin=bundle_ready and len(hashes) > 0,
    )


@router.post("/v1/admin/verify", response_model=OkResponse)
def verify_admin_pin(body: AdminVerifyBody, db: Session = Depends(get_db)) -> OkResponse:
    if not body.pin.isdigit():
        raise HTTPException(status_code=401, detail="Invalid admin code")
    bundle = _bundle_dict_optional(db)
    if bundle is None:
        raise HTTPException(status_code=401, detail="Invalid admin code")
    hashes = bundle.get("admin_pin_hashes") or []
    if not hashes:
        raise HTTPException(status_code=401, detail="no_admin_pins_configured")
    for h in hashes:
        if not h or not isinstance(h, str):
            continue
        try:
            if verify_password(body.pin, h):
                return OkResponse()
        except Exception:
            continue
    raise HTTPException(status_code=401, detail="Invalid admin code")
@router.post("/v1/printers/test-receipt", response_model=EscposPayloadResponse)
def printer_test_receipt(
    body: PrinterTestReceiptBody | None = None, db: Session = Depends(get_db)
) -> EscposPayloadResponse:
    event_name = "Test"
    currency = "EUR"
    articles = {"1": {"id": 1, "name": "Testartikel", "price": 1.0, "additions": []}}
    ev: dict | None = None
    event_id = body.event_id if body else None
    if event_id:
        bundle = get_bundle_dict(db)
        ev = event_from_bundle(bundle, event_id)
        if not ev:
            raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
        event_name = ev.get("name", "Event")
        currency = ev.get("currency", "EUR")
        articles = _article_map(ev) or articles
    payload = {
        "event_id": event_id,
        "table_number": 1,
        "waiter_name": "Test",
        "lines": [{"article_id": 1, "qty": 1, "article_name": "Testartikel", "note": "Bluetooth Test", "additions": []}],
        "payments": [{"type": "cash", "amount_cents": 100}],
        "payment_status": "paid",
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }
    esc = build_payment_receipt_text(
        payload,
        event_name,
        articles=articles,
        currency=currency,
        generated_at=payload["paid_at"],
        event=ev,
        paper_width=body.paper_width if body else None,
    )
    return EscposPayloadResponse(escpos_payload=base64.b64encode(esc).decode("ascii"))


def _first_article_id_for_station_test(st: dict, ev: dict) -> int | None:
    ids = st.get("article_ids") or []
    if ids:
        return int(ids[0])
    arts = ev.get("articles") or {}
    for key in sorted(arts.keys(), key=lambda k: (0, int(k)) if str(k).isdigit() else (1, str(k))):
        entry = arts[key]
        if isinstance(entry, dict) and entry.get("id") is not None:
            return int(entry["id"])
        if str(key).isdigit():
            return int(key)
    return None


def _sample_test_lines_for_station(st: dict, ev: dict) -> list[dict]:
    aid = _first_article_id_for_station_test(st, ev)
    if aid is None:
        return []
    arts = _article_map(ev)
    art = arts.get(str(aid)) or arts.get(aid) or {}
    name = art.get("name") or "Testdruck"
    return [
        {
            "article_id": aid,
            "qty": 1,
            "article_name": name,
            "note": "Größe / Crème brûlée",
            "additions": [],
        }
    ]


def _sorted_event_stations(ev: dict) -> list[dict]:
    stations = list((ev.get("configuration") or {}).get("stations") or [])
    return sorted(
        stations,
        key=lambda st: (int(st.get("sort_order") or 0), str(st.get("name") or "").lower()),
    )


@router.post("/v1/printers/test-station-prints", response_model=PrinterTestStationPrintsResponse)
async def printer_test_station_prints(
    body: PrinterTestStationPrintsBody, db: Session = Depends(get_db)
) -> PrinterTestStationPrintsResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    stations = _sorted_event_stations(ev)
    if not stations:
        raise HTTPException(status_code=422, detail="Keine Stationen in der Event-Konfiguration")

    event_name = ev.get("name", "Event")
    arts = _article_map(ev)
    now = datetime.now(timezone.utc).isoformat()
    results: list[StationTestPrintResult] = []
    printed = 0
    failed = 0

    for st in stations:
        station_uuid = str(st.get("uuid") or "").strip()
        if not station_uuid:
            failed += 1
            results.append(
                StationTestPrintResult(
                    station_uuid="",
                    station_name=str(st.get("name") or "Unbenannt"),
                    printer_host="",
                    printer_port=9100,
                    ok=False,
                    error="Station ohne UUID",
                )
            )
            continue

        station_name = station_name_from_event(ev, station_uuid)
        host, port, feed_lines = resolve_printer_endpoint(ev, station_uuid)
        payload = {
            "event_id": body.event_id,
            "table_number": 1,
            "waiter_name": "Testdruck",
            "ordered_at": now,
            "lines": _sample_test_lines_for_station(st, ev),
        }
        esc = build_escpos_station_test_slip(
            payload,
            event_name,
            station_name=station_name,
            articles=arts,
            event=ev,
            feed_lines=feed_lines,
        )
        try:
            await _send_to_printer(host, port, esc)
            printed += 1
            results.append(
                StationTestPrintResult(
                    station_uuid=station_uuid,
                    station_name=station_name,
                    printer_host=host,
                    printer_port=port,
                    ok=True,
                    error=None,
                )
            )
        except Exception as e:
            failed += 1
            results.append(
                StationTestPrintResult(
                    station_uuid=station_uuid,
                    station_name=station_name,
                    printer_host=host,
                    printer_port=port,
                    ok=False,
                    error=str(e)[:500],
                )
            )

    return PrinterTestStationPrintsResponse(
        event_id=body.event_id,
        printed=printed,
        failed=failed,
        results=results,
    )


WAITER_PRINT_JOB_KINDS = ("station_order", "kitchen_ticket")


def _print_job_created_at_iso(job: PrintJob) -> str | None:
    if job.created_at is not None:
        return job.created_at.isoformat()
    return None


def _serialize_print_job(
    job: PrintJob,
    order: LocalOrder | None,
    ev: dict | None,
) -> PrintJobSummary:
    payload: dict = {}
    if order is not None:
        try:
            payload = json.loads(order.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
    station_name = station_name_from_event(ev, job.station_uuid) if ev else None
    order_number = order.order_number if order is not None else None
    if order_number is None and payload.get("order_number") is not None:
        try:
            order_number = int(payload["order_number"])
        except (TypeError, ValueError):
            order_number = None
    table_number = order.table_number if order is not None else None
    if (not table_number) and payload.get("table_number"):
        try:
            table_number = int(payload["table_number"])
        except (TypeError, ValueError):
            table_number = None
    return PrintJobSummary(
        id=job.id,
        local_order_id=job.local_order_id,
        printer_host=job.printer_host,
        status=job.status,
        last_error=job.last_error,
        station_uuid=job.station_uuid,
        station_name=station_name,
        table_number=table_number or None,
        order_number=order_number,
        job_kind=job.job_kind,
        event_id=order.event_id if order is not None else None,
        created_at=_print_job_created_at_iso(job),
    )


def _parse_print_job_kinds(kinds: str | None) -> list[str]:
    if kinds and kinds.strip():
        return [k.strip() for k in kinds.split(",") if k.strip()]
    return list(WAITER_PRINT_JOB_KINDS)


@router.get("/v1/print-jobs", response_model=list[PrintJobSummary])
def list_print_jobs(
    db: Session = Depends(get_db),
    status: str | None = Query(None),
    waiter_uuid: str | None = Query(None),
    event_id: int | None = Query(None),
    kinds: str | None = Query(None, description="Comma-separated job_kind values"),
) -> list[PrintJobSummary]:
    filtered = status is not None or waiter_uuid is not None or event_id is not None or kinds is not None
    if not filtered:
        rows = db.query(PrintJob).order_by(PrintJob.id.desc()).limit(50).all()
        return [
            PrintJobSummary(
                id=r.id,
                local_order_id=r.local_order_id,
                printer_host=r.printer_host,
                status=r.status,
                last_error=r.last_error,
            )
            for r in rows
        ]

    kind_list = _parse_print_job_kinds(kinds)
    q = (
        db.query(PrintJob, LocalOrder)
        .join(LocalOrder, PrintJob.local_order_id == LocalOrder.id)
        .filter(LocalOrder.order_source == "waiter")
    )
    if waiter_uuid:
        q = q.filter(LocalOrder.waiter_uuid == waiter_uuid.strip())
    if event_id is not None:
        q = q.filter(LocalOrder.event_id == event_id)
    if status:
        q = q.filter(PrintJob.status == status.strip())
    if kind_list:
        q = q.filter(PrintJob.job_kind.in_(kind_list))
    rows = q.order_by(PrintJob.id.desc()).limit(50).all()
    bundle = get_bundle_dict(db)
    return [
        _serialize_print_job(job, order, event_from_bundle(bundle, order.event_id))
        for job, order in rows
    ]


@router.get("/v1/print-jobs/{job_id}", response_model=PrintJobSummary)
def get_print_job(job_id: int, db: Session = Depends(get_db)) -> PrintJobSummary:
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Print job not found")
    order = db.query(LocalOrder).filter(LocalOrder.id == job.local_order_id).first()
    ev = None
    if order is not None:
        bundle = get_bundle_dict(db)
        ev = event_from_bundle(bundle, order.event_id)
    return _serialize_print_job(job, order, ev)


@router.post("/v1/print-jobs/{job_id}/retry", response_model=PrintJobRetryResponse)
def retry_print_job(job_id: int, db: Session = Depends(get_db)) -> PrintJobRetryResponse:
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Print job not found")
    if job.status != "error":
        raise HTTPException(
            status_code=409,
            detail=f"Print job status is {job.status!r}; only failed jobs can be retried",
        )
    job.status = "queued"
    job.last_error = None
    db.commit()
    return PrintJobRetryResponse(print_job_id=job.id, status=job.status)


@router.delete("/v1/print-jobs/{job_id}", response_model=OkResponse)
def delete_print_job(job_id: int, db: Session = Depends(get_db)) -> OkResponse:
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Print job not found")
    if job.status != "error":
        raise HTTPException(
            status_code=409,
            detail=f"Print job status is {job.status!r}; only failed jobs can be deleted",
        )
    if job.job_kind not in WAITER_PRINT_JOB_KINDS:
        raise HTTPException(
            status_code=409,
            detail=f"Print job kind is {job.job_kind!r}; only waiter station/kitchen jobs can be deleted",
        )
    db.delete(job)
    db.commit()
    return OkResponse()


class PreviewLine(BaseModel):
    text: str = ""
    align: Literal["left", "center", "right"] = "left"
    size: Literal["small", "normal", "large", "xlarge"] = "normal"
    scale: int | None = None
    bold: bool = False
    kind: Literal["text", "logo"] = "text"


class EmulatedReceiptSummary(BaseModel):
    id: int
    job_kind: str | None = None
    station_name: str | None = None
    preview_text: str
    preview_lines: list[PreviewLine] = []
    created_at: str | None = None


class EmulatedReceiptDetail(EmulatedReceiptSummary):
    escpos_payload: str


def _emulated_receipt_preview_lines(row: EmulatedReceipt) -> list[PreviewLine]:
    from ..emulated_printer import escpos_bytes_to_preview_lines

    try:
        raw = base64.b64decode(row.escpos_payload or "")
    except Exception:
        return []
    return [PreviewLine(**line) for line in escpos_bytes_to_preview_lines(raw)]


def _emulated_receipt_summary(row: EmulatedReceipt) -> EmulatedReceiptSummary:
    return EmulatedReceiptSummary(
        id=row.id,
        job_kind=row.job_kind,
        station_name=row.station_name,
        preview_text=row.preview_text or "",
        preview_lines=_emulated_receipt_preview_lines(row),
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get("/v1/emulated-receipts", response_model=list[EmulatedReceiptSummary])
def list_emulated_receipts(db: Session = Depends(get_db)) -> list[EmulatedReceiptSummary]:
    from ..emulated_printer import is_emulated_printer_mode

    if not is_emulated_printer_mode():
        raise HTTPException(status_code=404, detail="Emulated printer mode is not enabled")
    rows = db.query(EmulatedReceipt).order_by(EmulatedReceipt.id.desc()).limit(100).all()
    return [_emulated_receipt_summary(row) for row in rows]


@router.get("/v1/emulated-receipts/{receipt_id}", response_model=EmulatedReceiptDetail)
def get_emulated_receipt(receipt_id: int, db: Session = Depends(get_db)) -> EmulatedReceiptDetail:
    from ..emulated_printer import is_emulated_printer_mode

    if not is_emulated_printer_mode():
        raise HTTPException(status_code=404, detail="Emulated printer mode is not enabled")
    row = db.query(EmulatedReceipt).filter(EmulatedReceipt.id == receipt_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Receipt not found")
    summary = _emulated_receipt_summary(row)
    return EmulatedReceiptDetail(
        **summary.model_dump(),
        escpos_payload=row.escpos_payload,
    )

from .edge_kitchen import router as edge_kitchen_router
from .edge_orders import router as edge_orders_router
from .edge_payments import router as edge_payments_router
from .edge_sync import router as edge_sync_router

router.include_router(edge_orders_router)
router.include_router(edge_kitchen_router)
router.include_router(edge_payments_router)
router.include_router(edge_sync_router)
