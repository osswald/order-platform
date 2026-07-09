"""Pi edge printer test routes."""

from __future__ import annotations

import base64
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..bundle_cache import event_from_bundle, get_bundle_dict
from ..deps import get_db
from ..print_worker import (
    _send_to_printer,
    build_escpos_station_test_slip,
    build_payment_receipt_text,
    station_name_from_event,
)
from ..printer_endpoint import resolve_printer_endpoint
from ..schemas.edge import (
    EscposPayloadResponse,
    PrinterTestReceiptBody,
    PrinterTestStationPrintsBody,
    PrinterTestStationPrintsResponse,
    StationTestPrintResult,
)
from .edge_common import _article_map

router = APIRouter()


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
        "paid_at": datetime.now(UTC).isoformat(),
    }
    esc = build_payment_receipt_text(
        payload,
        event_name,
        articles=articles,
        currency=currency,
        generated_at=payload["paid_at"],
        event=ev,
        paper_width=body.paper_width if body else None,
        charset=body.charset if body else None,
        test_charset_banner=True,
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
    now = datetime.now(UTC).isoformat()
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
