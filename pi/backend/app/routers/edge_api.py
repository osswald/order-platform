"""Edge API router — wires admin, printer, print job, and domain sub-routers."""

from fastapi import APIRouter

from .edge_admin import router as edge_admin_router
from .edge_emulated_receipts import router as edge_emulated_receipts_router
from .edge_kitchen import router as edge_kitchen_router
from .edge_orders import router as edge_orders_router
from .edge_payments import router as edge_payments_router
from .edge_print_jobs import router as edge_print_jobs_router
from .edge_printer_test import router as edge_printer_test_router
from .edge_sync import router as edge_sync_router

router = APIRouter()
router.include_router(edge_admin_router)
router.include_router(edge_printer_test_router)
router.include_router(edge_print_jobs_router)
router.include_router(edge_emulated_receipts_router)
router.include_router(edge_orders_router)
router.include_router(edge_kitchen_router)
router.include_router(edge_payments_router)
router.include_router(edge_sync_router)
