"""Event asset routes (TWINT QR, stock)."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..ingredient_stock import ensure_ingredient_stock_rows, upsert_ingredient_stock_rows
from ..ingredients import article_ids_with_ingredients, organisation_ingredients_enabled
from ..models import Article, Ingredient, User
from ..payment_types_config import payment_types_from_event
from ..schemas.event_stock import (
    EventIngredientStockItemRead,
    EventStockItemRead,
    EventStockListRead,
    EventStockUpdateIn,
)
from ..stock import bundle_article_ids, ensure_stock_rows_for_event_articles, upsert_stock_rows
from ..tenancy import TenantContext, get_current_tenant
from ..twint_qr import clear_twint_qr, store_twint_qr, twint_qr_bytes
from .events_helpers import get_event_for_configuration

router = APIRouter()


def _event_stock_response(db: Session, event) -> EventStockListRead:

    rows = ensure_stock_rows_for_event_articles(db, event, commit=False)
    composite = set()
    if organisation_ingredients_enabled(db, event.organisation_id):
        composite = article_ids_with_ingredients(db, bundle_article_ids(event))
    art_by_id = {a.id: a for a in db.query(Article).filter(Article.id.in_([r.article_id for r in rows])).all()}
    items = []
    for row in rows:
        if row.article_id in composite:
            continue
        art = art_by_id.get(row.article_id)
        if not art:
            continue
        items.append(
            EventStockItemRead(
                id=art.id,
                name=art.name,
                label=art.label,
                monitor_stock=row.monitor_stock,
                initial_in_stock=row.baseline_in_stock,
                in_stock=row.in_stock,
            )
        )
    items.sort(key=lambda x: x.name.lower())

    ingredients_out: list[EventIngredientStockItemRead] = []
    if organisation_ingredients_enabled(db, event.organisation_id):
        ing_rows = ensure_ingredient_stock_rows(db, event, commit=False)
        ing_by_id = {
            i.id: i for i in db.query(Ingredient).filter(Ingredient.id.in_([r.ingredient_id for r in ing_rows])).all()
        }
        for row in ing_rows:
            ing = ing_by_id.get(row.ingredient_id)
            if not ing:
                continue
            qty = float(row.in_stock) if row.in_stock is not None else None
            ingredients_out.append(
                EventIngredientStockItemRead(
                    id=ing.id,
                    name=ing.name,
                    unit=ing.unit,
                    monitor_stock=row.monitor_stock,
                    initial_in_stock=float(row.baseline_in_stock) if row.baseline_in_stock is not None else None,
                    in_stock=qty,
                )
            )
        ingredients_out.sort(key=lambda x: x.name.lower())

    return EventStockListRead(ingredients=ingredients_out, items=items)


@router.get("/{event_id}/twint-qr")
def get_event_twint_qr(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    payload = twint_qr_bytes(event)
    if not payload:
        raise api_error("no_twint_qr", status.HTTP_404_NOT_FOUND)
    mime, raw = payload
    return Response(content=raw, media_type=mime)


@router.put("/{event_id}/twint-qr")
async def put_event_twint_qr(
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    if "twint" not in payment_types_from_event(event):
        raise api_error("enable_twint_before_qr", status.HTTP_400_BAD_REQUEST)
    mime = (file.content_type or "").split(";")[0].strip().lower()
    raw = await file.read()
    try:
        store_twint_qr(event, mime, raw)
    except ValueError as e:
        raise api_error("validation_failed", status.HTTP_400_BAD_REQUEST) from e
    commit_or_raise(db)
    db.refresh(event)
    return {"ok": True, "has_twint_qr": True}


@router.delete("/{event_id}/twint-qr", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_twint_qr(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    clear_twint_qr(event)
    commit_or_raise(db)


@router.get("/{event_id}/event-stock", response_model=EventStockListRead)
def read_event_stock(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    commit_or_raise(db)
    return _event_stock_response(db, event)


@router.put("/{event_id}/event-stock", response_model=EventStockListRead)
def put_event_stock(
    event_id: int,
    body: EventStockUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    try:
        if body.items:
            upsert_stock_rows(
                db,
                event,
                [
                    {
                        "article_id": i.article_id,
                        "monitor_stock": i.monitor_stock,
                        **i.model_dump(exclude={"article_id", "monitor_stock"}, exclude_unset=True),
                    }
                    for i in body.items
                ],
            )
        if body.ingredients and organisation_ingredients_enabled(db, event.organisation_id):
            upsert_ingredient_stock_rows(
                db,
                event,
                [
                    {
                        "ingredient_id": i.ingredient_id,
                        "monitor_stock": i.monitor_stock,
                        **i.model_dump(exclude={"ingredient_id", "monitor_stock"}, exclude_unset=True),
                    }
                    for i in body.ingredients
                ],
            )
        commit_or_raise(db)
    except HTTPException:
        db.rollback()
        raise
    return _event_stock_response(db, event)
