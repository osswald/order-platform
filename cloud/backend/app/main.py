import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .csrf import CookieCsrfMiddleware
from .csrf import allowed_origins as csrf_allowed_origins
from .database import SessionLocal, apply_schema_patches, run_migrations
from .i18n import resolve_locale_from_accept_language
from .i18n.context import set_request_locale
from .models import User
from .rate_limit import limiter
from .roles import ROLE_PLATFORM_ADMIN
from .routers import (
    accounting_accounts,
    appliances,
    article_categories,
    articles,
    auth,
    color_palette,
    countries,
    edge,
    events,
    health,
    hire_companies,
    hosted_pi,
    ingredients,
    organisations,
    payment_types,
    position_comments,
    receipt_printing,
    stripe_connect,
    stripe_terminal,
    stripe_webhooks,
    tax_codes,
    users,
    waiters,
)
from .security import get_password_hash

log = logging.getLogger(__name__)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
# Keep CSRF allowlist in sync with CORS at import time.
csrf_allowed_origins[:] = allowed_origins


def _bootstrap_admin_user() -> None:
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == admin_email).first()
        if existing:
            if not getattr(existing, "role", None) or existing.role == "member":
                existing.role = ROLE_PLATFORM_ADMIN
                existing.is_superuser = True
                db.commit()
            return
        db.add(
            User(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                is_superuser=True,
                role=ROLE_PLATFORM_ADMIN,
            ),
        )
        db.commit()
    finally:
        db.close()


async def _hosted_pi_maintenance_loop() -> None:
    from .deps import SessionLocal
    from .hosted_pi_service import (
        cleanup_orphaned_hosted_appliances,
        expire_due_instances,
        reconcile_stuck_provisioning,
    )

    while True:
        try:
            db = SessionLocal()
            try:
                await expire_due_instances(db)
                await reconcile_stuck_provisioning(db)
                cleanup_orphaned_hosted_appliances(db)
            finally:
                db.close()
        except Exception:
            log.exception("hosted Pi maintenance cycle failed")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    run_migrations()
    apply_schema_patches()
    _bootstrap_admin_user()
    maintenance_task = asyncio.create_task(_hosted_pi_maintenance_loop())
    try:
        yield
    finally:
        maintenance_task.cancel()
        try:
            await maintenance_task
        except asyncio.CancelledError:
            pass


_app_env = os.getenv("APP_ENV", "").lower()
_openapi_default = "false" if _app_env == "production" else "true"
_enable_openapi = os.getenv("ENABLE_OPENAPI", _openapi_default).lower() == "true"
_openapi_url = "/openapi.json" if _enable_openapi else None
_docs_url = "/docs" if _enable_openapi else None
_redoc_url = "/redoc" if _enable_openapi else None

app = FastAPI(
    title=os.getenv("APP_NAME", "cloud-backend"),
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CookieCsrfMiddleware)


@app.middleware("http")
async def locale_middleware(request: Request, call_next):
    set_request_locale(resolve_locale_from_accept_language(request.headers.get("accept-language")))
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(countries.router, prefix="/countries", tags=["countries"])
app.include_router(hire_companies.router, prefix="/hire-companies", tags=["hire-companies"])
app.include_router(receipt_printing.router, tags=["receipt-printing"])
app.include_router(position_comments.router, tags=["position-comments"])
app.include_router(color_palette.router, tags=["color-palette"])
app.include_router(organisations.router, prefix="/organisations", tags=["organisations"])
app.include_router(appliances.router, prefix="/appliances", tags=["appliances"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(hosted_pi.router, prefix="/events", tags=["hosted-pi"])
app.include_router(waiters.router, prefix="/waiters", tags=["waiters"])
app.include_router(article_categories.router, prefix="/article-categories", tags=["article-categories"])
app.include_router(tax_codes.router, prefix="/tax-codes", tags=["tax-codes"])
app.include_router(payment_types.router, prefix="/payment-types", tags=["payment-types"])
app.include_router(accounting_accounts.router, prefix="/accounting-accounts", tags=["accounting-accounts"])
app.include_router(articles.router, prefix="/articles", tags=["articles"])
app.include_router(ingredients.router, prefix="/ingredients", tags=["ingredients"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(edge.router, prefix="/edge", tags=["edge"])
app.include_router(stripe_connect.router, prefix="/stripe/connect", tags=["stripe-connect"])
app.include_router(stripe_webhooks.router, prefix="/stripe", tags=["stripe-webhooks"])
app.include_router(stripe_terminal.router, prefix="/edge", tags=["stripe-terminal"])
