import os

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA cache_size=-8192")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA mmap_size=67108864")
    cursor.close()


def _create_all_tables() -> None:
    from . import models  # noqa: F401
    from . import models_operational  # noqa: F401

    Base.metadata.create_all(bind=engine)


def run_migrations() -> None:
    """Apply Alembic migrations to head; always ensure ORM metadata tables exist."""
    try:
        from alembic import command
        from alembic.config import Config

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = Config(os.path.join(root, "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
        command.upgrade(cfg, "head")
    except Exception:
        pass
    _create_all_tables()


def apply_schema_patches() -> None:
    """Deprecated: use run_migrations()."""
    run_migrations()
