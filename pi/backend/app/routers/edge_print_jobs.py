"""Pi edge print job routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..bundle_cache import event_from_bundle, get_bundle_dict
from ..deps import get_db
from ..models import LocalOrder, PrintJob
from ..print_worker import station_name_from_event
from ..schemas.edge import OkResponse, PrintJobRetryResponse, PrintJobSummary

router = APIRouter()

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
