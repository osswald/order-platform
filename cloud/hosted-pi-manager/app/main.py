"""Hosted Pi container orchestrator."""

import logging
import os

from fastapi import Depends, FastAPI, Header, HTTPException, Path, status
from pydantic import BaseModel, Field, field_validator

from .compose import destroy, provision
from .slug import validate_slug

log = logging.getLogger(__name__)
app = FastAPI(title=os.getenv("APP_NAME", "hosted-pi-manager"))


class ProvisionRequest(BaseModel):
    slug: str = Field(..., min_length=12, max_length=12)
    cloud_base_url: str
    edge_client_id: str
    edge_secret: str

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, value: str) -> str:
        return validate_slug(value)


def _verify_secret(x_manager_secret: str | None = Header(default=None, alias="X-Manager-Secret")) -> None:
    expected = os.getenv("HOSTED_PI_MANAGER_SECRET", "")
    if not expected or x_manager_secret != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/internal/instances", dependencies=[Depends(_verify_secret)])
def create_instance(body: ProvisionRequest):
    try:
        provision(
            body.slug,
            cloud_base_url=body.cloud_base_url.rstrip("/"),
            edge_client_id=body.edge_client_id,
            edge_secret=body.edge_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("provision failed for %s", body.slug)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)[:2000]) from exc
    return {"status": "running", "slug": body.slug}


@app.delete("/internal/instances/{slug}", dependencies=[Depends(_verify_secret)])
def delete_instance(slug: str = Path(..., min_length=12, max_length=12)):
    try:
        validate_slug(slug)
        destroy(slug)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("destroy failed for %s", slug)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)[:2000]) from exc
    return {"status": "stopped", "slug": slug}
