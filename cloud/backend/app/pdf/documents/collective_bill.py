"""Sammelrechnung (collective bill) PDF document."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ...event_sales import payment_type_label
from ...i18n import t
from ...models import Event, Organisation
from ..base import VqPdf
from ..formatting import format_datetime, format_event_range, format_money, organisation_issuer_lines
from ..logo import resolve_logo_for_event
from ..tables import TableColumn, TableSpec, write_table_header, write_table_row


def _positions_table_spec(pdf: VqPdf, locale: str) -> TableSpec:
    usable = pdf.content_width
    return TableSpec(
        columns=(
            TableColumn(t("pdf.collective_bill.article", locale), usable * 0.50, "L"),
            TableColumn(t("pdf.collective_bill.qty", locale), usable * 0.10, "R"),
            TableColumn(t("pdf.collective_bill.unit_price", locale), usable * 0.18, "R"),
            TableColumn(t("pdf.collective_bill.amount", locale), usable * 0.22, "R"),
        )
    )


def _article_cell(name: str, additions: list[dict] | None, note: str | None = None) -> str:
    lines = [name or "—"]
    for add in additions or []:
        add_name = add.get("name") or "—"
        add_qty = add.get("qty")
        if add_qty and int(add_qty) > 1:
            lines.append(f"  + {add_name} (×{add_qty})")
        else:
            lines.append(f"  + {add_name}")
    note_text = str(note or "").strip()
    if note_text:
        lines.append(f"  {note_text}")
    return "\n".join(lines)


def _line_group_row(group: dict, *, locale: str, currency: str) -> list[str]:
    qty = max(1, int(group.get("total_qty") or group.get("qty") or 1))
    unit_cents = group.get("unit_cents")
    if unit_cents is None:
        line_total = int(group.get("line_total_cents") or group.get("line_cents") or 0)
        unit_cents = line_total // qty if qty else line_total
    line_total = int(group.get("line_total_cents") or group.get("line_cents") or 0)
    return [
        _article_cell(str(group.get("name") or "—"), group.get("additions"), group.get("note")),
        str(qty),
        format_money(int(unit_cents), locale=locale, currency=currency),
        format_money(line_total, locale=locale, currency=currency),
    ]


def _collect_payments(orders: list[dict]) -> list[dict[str, Any]]:
    payments: list[dict[str, Any]] = []
    for order in orders:
        order_time = (
            order.get("ordered_at")
            or order.get("created_at")
        )
        for payment in order.get("payments") or []:
            if not isinstance(payment, dict):
                continue
            payments.append(
                {
                    "type": payment.get("type") or "other",
                    "amount_cents": int(payment.get("amount_cents") or 0),
                    "at": payment.get("paid_at") or payment.get("created_at") or order_time,
                }
            )
    return payments


def build_collective_bill_pdf(
    *,
    event: Event,
    organisation: Organisation,
    bill: dict[str, Any],
    currency: str,
    locale: str = "de",
) -> bytes:
    mime, logo_bytes = resolve_logo_for_event(event)
    _ = mime

    pdf = VqPdf(locale=locale, title=bill.get("name") or "Sammelrechnung")
    issuer_lines = organisation_issuer_lines(organisation)
    pdf.write_logo_header_block(logo_bytes, issuer_lines)

    pdf.write_heading(t("pdf.collective_bill.title", locale))
    pdf.write_text(t("pdf.collective_bill.for_recipient", locale, name=bill.get("name") or "—"))
    pdf.write_text(t("pdf.collective_bill.event", locale, name=event.name))
    pdf.write_muted(
        format_event_range(
            event.start.isoformat() if event.start else None,
            event.end.isoformat() if event.end else None,
            locale,
        )
    )
    pdf.write_spacer(3)

    table = _positions_table_spec(pdf, locale)
    pdf.write_text(t("pdf.collective_bill.summary_heading", locale), size=11)
    pdf.write_spacer(1)
    write_table_header(pdf, table)
    line_groups = bill.get("line_groups") or []
    if not line_groups:
        pdf.write_muted(t("pdf.collective_bill.no_positions", locale))
    else:
        for group in line_groups:
            write_table_row(pdf, table, _line_group_row(group, locale=locale, currency=currency))

    orders = bill.get("orders") or []
    if orders:
        pdf.write_spacer(4)
        pdf.write_text(t("pdf.collective_bill.orders_heading", locale), size=11)
        pdf.write_spacer(1)
        for order in orders:
            order_no = order.get("order_number")
            order_label = (
                t("pdf.collective_bill.order_heading", locale, number=order_no)
                if order_no is not None
                else t("pdf.collective_bill.order_heading_unknown", locale)
            )
            order_time = format_datetime(order.get("ordered_at") or order.get("created_at"), locale)
            pdf.ensure_vertical_space(22)
            pdf.write_text(f"{order_label} · {order_time}", size=10)
            write_table_header(pdf, table)
            for line in order.get("lines") or []:
                qty = max(1, int(line.get("qty") or 1))
                line_cents = int(line.get("line_cents") or 0)
                pseudo_group = {
                    "name": line.get("name"),
                    "note": line.get("note"),
                    "additions": line.get("additions"),
                    "total_qty": qty,
                    "unit_cents": line_cents // qty if qty else line_cents,
                    "line_total_cents": line_cents,
                }
                write_table_row(
                    pdf,
                    table,
                    _line_group_row(pseudo_group, locale=locale, currency=currency),
                )
            pdf.write_spacer(2)

    pdf.write_spacer(3)
    pdf.write_text(t("pdf.collective_bill.payments_heading", locale), size=11)
    pdf.write_text(
        t(
            "pdf.collective_bill.totals_line",
            locale,
            total=format_money(bill.get("line_cents"), locale=locale, currency=currency),
            paid=format_money(bill.get("paid_cents"), locale=locale, currency=currency),
            open_amount=format_money(bill.get("open_cents"), locale=locale, currency=currency),
        )
    )
    payments = _collect_payments(orders)
    if payments:
        for payment in payments:
            pdf.write_text(
                t(
                    "pdf.collective_bill.payment_line",
                    locale,
                    method=payment_type_label(str(payment.get("type") or "other")),
                    amount=format_money(payment.get("amount_cents"), locale=locale, currency=currency),
                    time=format_datetime(payment.get("at"), locale),
                ),
                size=9,
            )
    elif int(bill.get("paid_cents") or 0) > 0:
        pdf.write_muted(t("pdf.collective_bill.payments_not_itemized", locale))
    else:
        pdf.write_muted(t("pdf.collective_bill.no_payments", locale))

    pdf.write_spacer(4)
    pdf.write_muted(
        t(
            "pdf.common.generated_at",
            locale,
            time=format_datetime(datetime.now(UTC).isoformat(), locale),
        )
    )
    return pdf.output_bytes()
