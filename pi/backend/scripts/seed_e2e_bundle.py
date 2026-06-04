#!/usr/bin/env python3
"""Seed a minimal synced bundle for Playwright Pi smoke tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parents[1]
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from app.database import SessionLocal
from app.stock import save_bundle

E2E_BUNDLE = {
    "organisation_id": 1,
    "events": [
        {
            "id": 1,
            "name": "E2E Test",
            "currency": "CHF",
            "payment_mode": "pay_later",
            "payment_types": ["cash"],
            "status": "test",
            "articles": {
                "10": {"id": 10, "name": "Bier", "price": 5.0, "additions": []},
            },
            "configuration": {
                "event_waiters": [
                    {"uuid": "waiter-e2e", "name": "Anna", "pin": "1234"},
                ],
                "stations": [
                    {"uuid": "station-bar", "name": "Bar", "article_ids": [10]},
                ],
                "app_layouts": [],
            },
        }
    ],
}


def main() -> None:
    db = SessionLocal()
    try:
        save_bundle(db, E2E_BUNDLE)
        db.commit()
        print(json.dumps({"ok": True, "events": len(E2E_BUNDLE["events"])}))
    finally:
        db.close()


if __name__ == "__main__":
    main()
