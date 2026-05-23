import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, apply_schema_patches
from .routers import health, items, auth, organisations, appliances, users, events, waiters, article_categories, articles, edge
from .security import get_password_hash
from .models import User

app = FastAPI(title=os.getenv("APP_NAME", "cloud-backend"))

# CORS
allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    # create tables
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    # create admin user from env if provided
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_email and admin_password:
        from .database import SessionLocal

        db = SessionLocal()
        try:
            existing = db.query(User).filter(User.email == admin_email).first()
            if not existing:
                user = User(email=admin_email, hashed_password=get_password_hash(admin_password), is_superuser=True)
                db.add(user)
                db.commit()
        finally:
            db.close()


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
