from .database import SessionLocal
from .models import SyncedBundle


def ensure_default_synced_bundle() -> None:
    db = SessionLocal()
    try:
        if db.query(SyncedBundle).filter(SyncedBundle.id == 1).first():
            return
        db.add(SyncedBundle(id=1, json_body="{}"))
        db.commit()
    finally:
        db.close()
