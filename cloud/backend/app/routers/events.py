"""Event routes — aggregates CRUD, configuration, reports, and asset sub-routers."""

from fastapi import APIRouter

from .events_assets import router as assets_router
from .events_configuration import router as configuration_router
from .events_crud import router as crud_router
from .events_helpers import event_response, get_event_for_configuration, serialize_event_configuration
from .events_reports import router as reports_router

router = APIRouter()
router.include_router(crud_router)
router.include_router(configuration_router)
router.include_router(reports_router)
router.include_router(assets_router)

__all__ = [
    "router",
    "event_response",
    "get_event_for_configuration",
    "serialize_event_configuration",
]
