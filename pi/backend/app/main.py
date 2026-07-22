import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models_operational  # noqa: F401
from .bootstrap import ensure_default_synced_bundle
from .database import SessionLocal, run_migrations
from .edge_config import is_edge_configured, write_edge_config
from .models import SyncedBundle  # noqa: F401
from .ota_freeze import sync_ota_freeze_from_db
from .print_worker import print_worker_loop
from .routers import edge_api, health, ops, setup, shift_session
from .sync_worker import sync_worker_loop

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

stop_print_worker: asyncio.Event | None = None
print_task: asyncio.Task | None = None
stop_sync_worker: asyncio.Event | None = None
sync_task: asyncio.Task | None = None


def _bootstrap_hosted_edge_config() -> None:
    if os.getenv("HOSTED_PI", "").strip() != "1":
        return
    if is_edge_configured():
        return
    base = os.getenv("CLOUD_BASE_URL", "").strip()
    cid = os.getenv("EDGE_CLIENT_ID", "").strip()
    secret = os.getenv("EDGE_SECRET", "").strip()
    if base and cid and secret:
        write_edge_config(cloud_base_url=base, edge_client_id=cid, edge_secret=secret)
        log.info("Hosted Pi edge credentials written to %s", os.getenv("EDGE_CONFIG_FILE", "/data/edge.env"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global stop_print_worker, print_task, stop_sync_worker, sync_task
    run_migrations()
    _bootstrap_hosted_edge_config()
    ensure_default_synced_bundle()
    try:
        with SessionLocal() as db:
            sync_ota_freeze_from_db(db)
    except Exception as exc:
        log.warning("OTA freeze sync on startup failed: %s", exc)

    stop_print_worker = asyncio.Event()
    print_task = asyncio.create_task(print_worker_loop(stop_print_worker))
    log.info("Print worker started")

    stop_sync_worker = asyncio.Event()
    sync_task = asyncio.create_task(sync_worker_loop(stop_sync_worker))
    log.info("Sync worker started")

    yield
    if stop_sync_worker:
        stop_sync_worker.set()
    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
    if stop_print_worker:
        stop_print_worker.set()
    if print_task:
        print_task.cancel()
        try:
            await print_task
        except asyncio.CancelledError:
            pass
    log.info("Shutdown complete")


app = FastAPI(title=os.getenv("APP_NAME", "pi-backend"), lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(setup.router, tags=["setup"])
app.include_router(edge_api.router, tags=["edge"])
app.include_router(ops.router, tags=["ops"])
app.include_router(shift_session.router, tags=["shift"])
