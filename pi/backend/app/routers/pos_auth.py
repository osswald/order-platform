from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..deps import get_db
from ..pos_auth import verify_register_pin, verify_waiter_pin
from ..schemas.edge import OkResponse
from .edge_api import _bundle_dict_optional

router = APIRouter(prefix="/v1/auth")


class WaiterPinVerifyBody(BaseModel):
    event_id: int
    waiter_uuid: str = Field(..., min_length=1)
    pin: str = Field(..., min_length=1, max_length=32)


class RegisterPinVerifyBody(BaseModel):
    event_id: int
    register_uuid: str = Field(..., min_length=1)
    pin: str = Field(..., min_length=1, max_length=32)


class PosPinVerifyResponse(OkResponse):
    name: str


@router.post("/waiter/verify", response_model=PosPinVerifyResponse)
def verify_waiter_login(body: WaiterPinVerifyBody, db: Session = Depends(get_db)) -> PosPinVerifyResponse:
    bundle = _bundle_dict_optional(db)
    if bundle is None:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    if not verify_waiter_pin(
        bundle,
        event_id=body.event_id,
        waiter_uuid=body.waiter_uuid,
        pin=body.pin,
    ):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    ev = next((e for e in bundle.get("events") or [] if int(e.get("id") or 0) == int(body.event_id)), None)
    name = ""
    if ev:
        for w in (ev.get("configuration") or {}).get("event_waiters") or []:
            if str(w.get("uuid")) == str(body.waiter_uuid):
                name = str(w.get("name") or "")
                break
    return PosPinVerifyResponse(name=name)


@router.post("/register/verify", response_model=PosPinVerifyResponse)
def verify_register_login(body: RegisterPinVerifyBody, db: Session = Depends(get_db)) -> PosPinVerifyResponse:
    bundle = _bundle_dict_optional(db)
    if bundle is None:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    if not verify_register_pin(
        bundle,
        event_id=body.event_id,
        register_uuid=body.register_uuid,
        pin=body.pin,
    ):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    ev = next((e for e in bundle.get("events") or [] if int(e.get("id") or 0) == int(body.event_id)), None)
    name = ""
    if ev:
        for reg in (ev.get("configuration") or {}).get("cash_registers") or []:
            if str(reg.get("uuid")) == str(body.register_uuid):
                name = str(reg.get("name") or "")
                break
    return PosPinVerifyResponse(name=name)
