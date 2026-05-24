import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import SessionLocal, apply_schema_patches, engine, Base
from .models import User
from .routers import (
    article_categories,
    articles,
    auth,
    edge,
    events,
    health,
    items,
    organisations,
    appliances,
    users,
    waiters,
)
from .security import get_password_hash

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]


def _bootstrap_admin_user() -> None:
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == admin_email).first()
        if existing:
            return
        db.add(
            User(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                is_superuser=True,
            ),
        )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    _bootstrap_admin_user()
    yield


app = FastAPI(title=os.getenv("APP_NAME", "cloud-backend"), lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(items.router, prefix="/items", tags=["items"])
app.include_router(organisations.router, prefix="/organisations", tags=["organisations"])
app.include_router(appliances.router, prefix="/appliances", tags=["appliances"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(waiters.router, prefix="/waiters", tags=["waiters"])
app.include_router(article_categories.router, prefix="/article-categories", tags=["article-categories"])
app.include_router(articles.router, prefix="/articles", tags=["articles"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(edge.router, prefix="/edge", tags=["edge"])
