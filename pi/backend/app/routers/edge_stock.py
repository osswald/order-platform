"""Stock validation routes for order submission."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..bundle_cache import event_from_bundle, get_bundle_dict
from ..deps import get_db
from ..schemas.edge import StockValidateOrderIn, StockValidateOrderResponse
from ..stock import validate_stock

router = APIRouter()


@router.post("/v1/stock/validate-order", response_model=StockValidateOrderResponse)
def validate_order_stock(body: StockValidateOrderIn, db: Session = Depends(get_db)) -> StockValidateOrderResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    line_dicts = [
        {
            "article_id": ln.article_id,
            "qty": ln.qty,
            "additions": [{"article_id": a.article_id, "qty": a.qty} for a in ln.additions],
        }
        for ln in body.lines
    ]
    validate_stock(ev, line_dicts)
    return StockValidateOrderResponse()
