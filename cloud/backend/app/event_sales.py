"""Sales report from edge-submitted order payloads."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from .additions import load_links_for_bases
from .models import Article, EdgeSubmittedOrder, Event, EventVoucherRedemption, Waiter


PAYMENT_TYPE_LABELS = {
    "cash": "Bargeld",
    "twint": "TWINT",
    "sumup": "SumUp",
    "stripe_terminal": "Karte (Stripe Terminal)",
    "instant": "Sofort",
    "open": "Offen",
}


def _normalize_payment_type(raw: str | None) -> str:
    t = (raw or "").strip().lower()
    return t if t else "other"


def payment_type_label(type_key: str) -> str:
    if type_key in PAYMENT_TYPE_LABELS:
        return PAYMENT_TYPE_LABELS[type_key]
    if type_key == "other":
        return "Sonstige"
    return type_key


def _article_entry(articles: dict, article_id) -> dict | None:
    return articles.get(int(article_id)) if article_id is not None else None


def _addition_price_cents(articles: dict, base_article: dict | None, addition_id: int) -> int:
    if base_article:
        for add in base_article.get("additions") or []:
            if int(add.get("article_id")) == int(addition_id):
                return int(round(float(add.get("price", 0)) * 100))
    a = _article_entry(articles, addition_id)
    if a and a.get("price") is not None:
        return int(round(float(a["price"]) * 100))
    return 0


def line_unit_cents(line: dict, articles: dict) -> int:
    if line.get("unit_cents") is not None:
        unit = int(line["unit_cents"])
    else:
        aid = line.get("article_id")
        base = _article_entry(articles, aid)
        price = float(base["price"]) if base and base.get("price") is not None else 0.0
        unit = int(round(price * 100))
    aid = line.get("article_id")
    base = _article_entry(articles, aid)
    for add in line.get("additions") or []:
        if not isinstance(add, dict):
            continue
        add_id = add.get("article_id")
        if add_id is None:
            continue
        add_qty = max(1, int(add.get("qty") or 1))
        if add.get("unit_cents") is not None:
            unit += int(add["unit_cents"]) * add_qty
        else:
            unit += _addition_price_cents(articles, base, int(add_id)) * add_qty
    return max(0, unit)


def distinct_order_numbers_from_payload(payload: dict, *, legacy_key: str) -> set:
    keys: set = set()
    doc = payload.get("order_number")
    lines = payload.get("lines") or []
    found = False
    for line in lines:
        if not isinstance(line, dict):
            continue
        qty = max(1, int(line.get("qty") or 1))
        if qty < 1:
            continue
        n = line.get("order_number")
        if n is not None:
            keys.add(int(n))
            found = True
        elif doc is not None:
            keys.add(int(doc))
            found = True
    if not found:
        keys.add(legacy_key)
    return keys


def distinct_order_numbers_for_rows(rows: list[EdgeSubmittedOrder]) -> int:
    keys: set = set()
    for row in rows:
        payload = row.payload if isinstance(row.payload, dict) else {}
        keys |= distinct_order_numbers_from_payload(payload, legacy_key=f"row:{row.id}")
    return len(keys)


def _line_for_pricing(line: dict) -> dict:
    additions = []
    for add in line.get("additions") or []:
        if not isinstance(add, dict):
            continue
        aid = add.get("article_id")
        if aid is None:
            continue
        entry: dict[str, Any] = {
            "article_id": int(aid),
            "qty": max(1, int(add.get("qty") or 1)),
        }
        if add.get("unit_cents") is not None:
            entry["unit_cents"] = int(add["unit_cents"])
        additions.append(entry)
    out: dict[str, Any] = {
        "article_id": int(line["article_id"]),
        "qty": max(1, int(line.get("qty") or 1)),
        "note": str(line.get("note") or ""),
        "additions": additions,
    }
    if line.get("unit_cents") is not None:
        out["unit_cents"] = int(line["unit_cents"])
    return out


def line_total_cents(line: dict, articles: dict) -> int:
    qty = max(1, int(line.get("qty") or 1))
    return line_unit_cents(line, articles) * qty


def _normalize_additions(additions: list | None) -> list[dict]:
    out = []
    for add in additions or []:
        if not isinstance(add, dict):
            continue
        aid = add.get("article_id")
        if aid is None:
            continue
        out.append({"article_id": int(aid), "qty": max(1, int(add.get("qty") or 1))})
    return out


def format_payload_lines(lines: list | None, articles: dict) -> list[dict]:
    """Format raw payload lines with names and amounts for API display."""
    out: list[dict] = []
    for line in lines or []:
        if not isinstance(line, dict):
            continue
        aid = line.get("article_id")
        if aid is None:
            continue
        aid_int = int(aid)
        qty = max(1, int(line.get("qty") or 1))
        additions = _normalize_additions(line.get("additions"))
        line_dict = _line_for_pricing(line)
        line_cents = line_total_cents(line_dict, articles)
        line_name = (
            line.get("article_name")
            or (articles.get(aid_int) or {}).get("name")
            or f"Artikel #{aid_int}"
        )
        art = articles.get(aid_int) or {}
        raw_adds = [a for a in (line.get("additions") or []) if isinstance(a, dict)]
        addition_lines = []
        for add in additions:
            add_id = add["article_id"]
            add_qty = add["qty"]
            add_art = articles.get(add_id) or {}
            raw_add = next((a for a in raw_adds if int(a.get("article_id") or 0) == add_id), None)
            if raw_add and raw_add.get("unit_cents") is not None:
                add_unit = int(raw_add["unit_cents"])
            else:
                add_unit = _addition_price_cents(articles, art, add_id)
            add_display_name = (
                (raw_add.get("name") if raw_add else None)
                or add_art.get("name")
                or f"Artikel #{add_id}"
            )
            addition_lines.append(
                {
                    "article_id": add_id,
                    "name": add_display_name,
                    "qty": add_qty,
                    "line_cents": add_unit * qty * add_qty,
                }
            )
        note = str(line.get("note") or "").strip()
        entry: dict[str, Any] = {
            "article_id": aid_int,
            "name": line_name,
            "qty": qty,
            "line_cents": line_cents,
            "additions": addition_lines,
        }
        if note:
            entry["note"] = note
        if line.get("order_number") is not None:
            entry["order_number"] = int(line["order_number"])
        out.append(entry)
    return out


def _build_station_maps(event: Event) -> tuple[dict[str, str], dict[int, str | None], dict[int, str]]:
    """station_uuid -> name; article_id -> station_uuid; legacy article_id -> station int id."""
    names_by_uuid: dict[str, str] = {}
    article_station_uuid: dict[int, str | None] = {}
    station_names_by_int: dict[int, str] = {}
    for st in event.stations or []:
        names_by_uuid[st.uuid] = st.name
        station_names_by_int[st.id] = st.name
        for a in st.articles or []:
            if a.id not in article_station_uuid:
                article_station_uuid[a.id] = st.uuid
    return names_by_uuid, article_station_uuid, station_names_by_int


def _fallback_station_label(station_uuid: str | None, station_id_int: int | None = None) -> str:
    if station_uuid:
        return f"Station {station_uuid[:8]}…"
    if station_id_int is not None:
        return f"Station #{station_id_int}"
    return "—"


def _fallback_waiter_label(waiter_uuid: str | None, waiter_id_int: int | None = None) -> str:
    if waiter_uuid:
        return f"Kellner {waiter_uuid[:8]}…"
    if waiter_id_int is not None:
        return f"Kellner #{waiter_id_int}"
    return "—"


def _is_generic_station_label(name: str) -> bool:
    return name in ("—", "Unbekannt") or name.startswith("Station ")


def _is_generic_waiter_label(name: str) -> bool:
    return name in ("—", "Unbekannt") or name.startswith("Kellner ")


def _payload_waiter_uuid(payload: dict) -> str | None:
    raw = payload.get("waiter_uuid")
    if raw is None or raw == "":
        return None
    return str(raw).strip() or None


def _payload_waiter_id_legacy(payload: dict) -> int | None:
    raw = payload.get("waiter_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _line_station_uuid(line: dict) -> str | None:
    raw = line.get("station_uuid")
    if raw is None or raw == "":
        return None
    return str(raw).strip() or None


def _line_station_id_legacy(line: dict) -> int | None:
    raw = line.get("station_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _build_name_maps(db: Session, event: Event) -> dict[str, Any]:
    names_by_uuid, article_station_uuid, station_names_by_int = _build_station_maps(event)
    waiter_by_uuid = {ew.uuid: ew.name for ew in event.event_waiters or []}
    waiter_by_int = {ew.id: ew.name for ew in event.event_waiters or []}
    waiter_by_source = {
        int(ew.source_waiter_id): ew.name
        for ew in event.event_waiters or []
        if ew.source_waiter_id is not None
    }
    global_waiter: dict[int, str] = {}
    org_id = getattr(event, "organisation_id", None)
    if org_id is not None:
        for w in db.query(Waiter).filter(Waiter.organisation_id == org_id).all():
            global_waiter[w.id] = w.name
    return {
        "station_names_by_uuid": names_by_uuid,
        "article_station_uuid": article_station_uuid,
        "station_names_by_int": station_names_by_int,
        "waiter_by_uuid": waiter_by_uuid,
        "waiter_by_int": waiter_by_int,
        "waiter_by_source": waiter_by_source,
        "global_waiter": global_waiter,
    }


def _resolve_station_name(
    line: dict,
    station_uuid: str | None,
    station_id_int: int | None,
    maps: dict[str, Any],
) -> str:
    if station_uuid:
        name = maps["station_names_by_uuid"].get(station_uuid)
        if name:
            return name
    if station_id_int is not None:
        name = maps["station_names_by_int"].get(station_id_int)
        if name:
            return name
    return _fallback_station_label(station_uuid, station_id_int)


def _resolve_waiter_name(
    payload: dict,
    waiter_uuid: str | None,
    waiter_id_int: int | None,
    maps: dict[str, Any],
) -> str:
    if waiter_uuid:
        name = maps["waiter_by_uuid"].get(waiter_uuid)
        if name:
            return name
    if waiter_id_int is not None:
        name = maps["waiter_by_int"].get(waiter_id_int)
        if name:
            return name
        name = maps["waiter_by_source"].get(waiter_id_int)
        if name:
            return name
        name = maps["global_waiter"].get(waiter_id_int)
        if name:
            return name
    return _fallback_waiter_label(waiter_uuid, waiter_id_int)


def _waiter_bucket_key(waiter_uuid: str | None, waiter_id_int: int | None) -> str | None:
    if waiter_uuid:
        return f"u:{waiter_uuid}"
    if waiter_id_int is not None:
        return f"i:{waiter_id_int}"
    return None


def _station_bucket_key(station_uuid: str | None, station_id_int: int | None) -> str | None:
    if station_uuid:
        return f"u:{station_uuid}"
    if station_id_int is not None:
        return f"i:{station_id_int}"
    return None


def _upgrade_bucket_name(current: str, candidate: str, is_generic) -> str:
    if is_generic(current) and not is_generic(candidate):
        return candidate
    return current


def _build_articles_pricing_map(db: Session, article_ids: set[int]) -> dict[int, dict]:
    if not article_ids:
        return {}
    arts = {
        a.id: a
        for a in db.query(Article).filter(Article.id.in_(list(article_ids))).all()
    }
    base_ids = {aid for aid, a in arts.items() if not a.is_addition}
    links_by_base = load_links_for_bases(db, base_ids)
    missing_add_ids: set[int] = set()
    for links in links_by_base.values():
        for link in links:
            if link.addition_article_id not in arts:
                missing_add_ids.add(int(link.addition_article_id))
    if missing_add_ids:
        for add_row in db.query(Article).filter(Article.id.in_(list(missing_add_ids))).all():
            arts[add_row.id] = add_row
    out: dict[int, dict] = {}
    for aid in article_ids:
        art = arts.get(aid)
        if not art:
            continue
        entry: dict[str, Any] = {
            "article_id": art.id,
            "name": art.name,
            "price": art.price,
            "additions": [],
        }
        if not art.is_addition and aid in links_by_base:
            for link in links_by_base[aid]:
                add_art = arts.get(link.addition_article_id)
                if add_art:
                    entry["additions"].append(
                        {
                            "article_id": add_art.id,
                            "name": add_art.name,
                            "price": add_art.price,
                        }
                    )
        out[aid] = entry
    return out


def _collect_article_ids_from_orders(rows: list[EdgeSubmittedOrder]) -> set[int]:
    ids: set[int] = set()
    for row in rows:
        payload = row.payload or {}
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            aid = line.get("article_id")
            if aid is not None:
                ids.add(int(aid))
            for add in line.get("additions") or []:
                if isinstance(add, dict) and add.get("article_id") is not None:
                    ids.add(int(add["article_id"]))
    return ids


def build_event_sales_report(db: Session, event: Event) -> dict[str, Any]:
    orders_rows = (
        db.query(EdgeSubmittedOrder)
        .filter(EdgeSubmittedOrder.event_id == event.id)
        .order_by(EdgeSubmittedOrder.created_at.desc(), EdgeSubmittedOrder.id.desc())
        .all()
    )

    maps = _build_name_maps(db, event)
    article_station_uuid = maps["article_station_uuid"]

    article_ids = _collect_article_ids_from_orders(orders_rows)
    articles = _build_articles_pricing_map(db, article_ids)

    currency = (getattr(event, "currency", None) or "CHF").upper()

    orders_out: list[dict] = []
    by_waiter: dict[str, dict] = {}
    by_station: dict[str, dict] = {}
    by_article: dict[int, dict] = {}
    by_payment: dict[str, int] = defaultdict(int)

    total_line_cents = 0
    total_paid_cents = 0
    total_open_cents = 0
    distinct_order_keys: set = set()

    for row in orders_rows:
        payload = row.payload if isinstance(row.payload, dict) else {}
        payment_status = str(payload.get("payment_status") or "open").lower()
        distinct_order_keys |= distinct_order_numbers_from_payload(payload, legacy_key=f"row:{row.id}")
        waiter_uuid = _payload_waiter_uuid(payload)
        waiter_id_int = _payload_waiter_id_legacy(payload)
        table_number = payload.get("table_number")

        payments_raw = [p for p in (payload.get("payments") or []) if isinstance(p, dict)]
        paid_cents = sum(max(0, int(p.get("amount_cents") or 0)) for p in payments_raw)
        order_waiter_name = _resolve_waiter_name(payload, waiter_uuid, waiter_id_int, maps)

        lines_out = []
        order_line_cents = 0

        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            aid = line.get("article_id")
            if aid is None:
                continue
            aid_int = int(aid)
            qty = max(1, int(line.get("qty") or 1))
            additions = _normalize_additions(line.get("additions"))
            line_dict = _line_for_pricing(line)
            line_cents = line_total_cents(line_dict, articles)
            line_name = line.get("article_name") or (articles.get(aid_int) or {}).get("name") or f"Artikel #{aid_int}"
            order_line_cents += line_cents

            station_uuid = _line_station_uuid(line)
            station_id_int = _line_station_id_legacy(line)
            if station_uuid is None and station_id_int is None:
                station_uuid = article_station_uuid.get(aid_int)
            station_label = _resolve_station_name(line, station_uuid, station_id_int, maps)

            art = articles.get(aid_int) or {}
            addition_lines = []
            raw_adds = [a for a in (line.get("additions") or []) if isinstance(a, dict)]
            for add in additions:
                add_id = add["article_id"]
                add_qty = add["qty"]
                add_art = articles.get(add_id) or {}
                raw_add = next((a for a in raw_adds if int(a.get("article_id") or 0) == add_id), None)
                if raw_add and raw_add.get("unit_cents") is not None:
                    add_unit = int(raw_add["unit_cents"])
                else:
                    add_unit = _addition_price_cents(articles, art, add_id)
                add_line_cents = add_unit * qty * add_qty
                add_display_name = (
                    (raw_add.get("name") if raw_add else None)
                    or add_art.get("name")
                    or f"Artikel #{add_id}"
                )
                addition_lines.append(
                    {
                        "article_id": add_id,
                        "name": add_display_name,
                        "qty": add_qty,
                        "line_cents": add_line_cents,
                    }
                )
                # Article breakdown: additions counted separately
                if add_id not in by_article:
                    by_article[add_id] = {
                        "article_id": add_id,
                        "name": add_art.get("name") or f"Artikel #{add_id}",
                        "qty": 0,
                        "line_cents": 0,
                    }
                by_article[add_id]["qty"] += qty * add_qty
                by_article[add_id]["line_cents"] += add_line_cents

            lines_out.append(
                {
                    "article_id": aid_int,
                    "name": line_name,
                    "qty": qty,
                    "station_uuid": station_uuid,
                    "station_name": station_label,
                    "line_cents": line_cents,
                    "additions": addition_lines,
                }
            )

            base_unit = int(line["unit_cents"]) if line.get("unit_cents") is not None else int(round(float(art.get("price") or 0) * 100))
            base_line_cents = base_unit * qty
            if aid_int not in by_article:
                by_article[aid_int] = {
                    "article_id": aid_int,
                    "name": line_name,
                    "qty": 0,
                    "line_cents": 0,
                }
            by_article[aid_int]["qty"] += qty
            by_article[aid_int]["line_cents"] += base_line_cents

            st_key = _station_bucket_key(station_uuid, station_id_int)
            if st_key is not None and st_key not in by_station:
                by_station[st_key] = {
                    "station_uuid": station_uuid,
                    "name": station_label,
                    "line_cents": 0,
                    "qty": 0,
                }
            elif st_key is not None:
                by_station[st_key]["name"] = _upgrade_bucket_name(
                    by_station[st_key]["name"],
                    station_label,
                    _is_generic_station_label,
                )
            if st_key is not None:
                by_station[st_key]["line_cents"] += line_cents
                by_station[st_key]["qty"] += qty

        total_line_cents += order_line_cents
        total_paid_cents += paid_cents

        w_key = _waiter_bucket_key(waiter_uuid, waiter_id_int)
        if w_key is not None:
            if w_key not in by_waiter:
                by_waiter[w_key] = {
                    "waiter_uuid": waiter_uuid,
                    "name": order_waiter_name,
                    "line_cents": 0,
                    "paid_cents": 0,
                    "order_count": 0,
                }
            else:
                by_waiter[w_key]["name"] = _upgrade_bucket_name(
                    by_waiter[w_key]["name"],
                    order_waiter_name,
                    _is_generic_waiter_label,
                )
            by_waiter[w_key]["line_cents"] += order_line_cents
            by_waiter[w_key]["paid_cents"] += paid_cents
            by_waiter[w_key]["order_count"] += 1

        if payment_status != "paid" and paid_cents == 0 and order_line_cents > 0:
            total_open_cents += order_line_cents
            by_payment["open"] += order_line_cents
        else:
            for p in payments_raw:
                pt = _normalize_payment_type(p.get("type"))
                amt = max(0, int(p.get("amount_cents") or 0))
                if pt not in PAYMENT_TYPE_LABELS and pt != "open":
                    key = pt if pt else "other"
                else:
                    key = pt
                by_payment[key] += amt

        orders_out.append(
            {
                "id": row.id,
                "client_order_id": row.client_order_id,
                "order_number": payload.get("order_number"),
                "ordered_at": payload.get("ordered_at"),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "table_number": table_number,
                "waiter_uuid": waiter_uuid,
                "waiter_name": order_waiter_name,
                "payment_status": payment_status,
                "line_cents": order_line_cents,
                "paid_cents": paid_cents,
                "lines": lines_out,
                "payments": [
                    {
                        "type": _normalize_payment_type(p.get("type")),
                        "type_label": payment_type_label(_normalize_payment_type(p.get("type"))),
                        "amount_cents": max(0, int(p.get("amount_cents") or 0)),
                    }
                    for p in payments_raw
                ],
            }
        )

    by_waiter_list = sorted(by_waiter.values(), key=lambda x: -x["line_cents"])
    by_station_list = sorted(by_station.values(), key=lambda x: -x["line_cents"])
    by_article_list = sorted(by_article.values(), key=lambda x: -x["line_cents"])
    by_payment_list = [
        {
            "type": k,
            "label": payment_type_label(k),
            "amount_cents": v,
        }
        for k, v in sorted(by_payment.items(), key=lambda x: -x[1])
    ]

    voucher_sold_cents = 0
    for row in orders_rows:
        payload = row.payload if isinstance(row.payload, dict) else {}
        for line in payload.get("lines") or []:
            if not isinstance(line, dict) or str(line.get("kind") or "") != "voucher_sale":
                continue
            unit = max(0, int(line.get("unit_cents") or 0))
            qty = max(1, int(line.get("qty") or 1))
            voucher_sold_cents += unit * qty

    redemption_rows = (
        db.query(EventVoucherRedemption).filter(EventVoucherRedemption.event_id == event.id).all()
    )
    voucher_redeemed_cents = sum(max(0, int(r.applied_cents or 0)) for r in redemption_rows)

    return {
        "currency": currency,
        "totals": {
            "orders_count": len(orders_out),
            "distinct_orders_count": len(distinct_order_keys),
            "line_cents": total_line_cents,
            "paid_cents": total_paid_cents,
            "open_cents": total_open_cents,
            "voucher_sold_cents": voucher_sold_cents,
            "voucher_redeemed_cents": voucher_redeemed_cents,
            "voucher_redemption_count": len(redemption_rows),
        },
        "orders": orders_out,
        "by_waiter": by_waiter_list,
        "by_station": by_station_list,
        "by_article": by_article_list,
        "by_payment_type": by_payment_list,
    }
