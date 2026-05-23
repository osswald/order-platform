import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base, SessionLocal, apply_schema_patches
from .models import SyncedBundle
from .print_worker import print_worker_loop
from .sync_worker import sync_worker_loop
from .routers import health, edge_api

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

stop_print_worker: asyncio.Event | None = None
print_task: asyncio.Task | None = None
stop_sync_worker: asyncio.Event | None = None
sync_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global stop_print_worker, print_task, stop_sync_worker, sync_task
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    db = SessionLocal()
    try:
        if not db.query(SyncedBundle).filter(SyncedBundle.id == 1).first():
            db.add(SyncedBundle(id=1, json_body="{}"))
            db.commit()
    finally:
        db.close()

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
app.include_router(edge_api.router, tags=["edge"])
