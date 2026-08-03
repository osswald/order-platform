from .bundle_cache import invalidate_bundle_cache
from .database import SessionLocal
from .models import SyncedBundle
from .models_operational import BundleMeta


def ensure_default_synced_bundle() -> None:
    db = SessionLocal()
    try:
        if not db.query(SyncedBundle).filter(SyncedBundle.id == 1).first():
            db.add(SyncedBundle(id=1, json_body="{}"))
            invalidate_bundle_cache()
        if not db.query(BundleMeta).filter(BundleMeta.id == 1).first():
            db.add(BundleMeta(id=1, pull_complete=0))
        db.commit()
    finally:
        db.close()
