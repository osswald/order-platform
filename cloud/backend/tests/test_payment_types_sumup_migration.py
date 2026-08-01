"""Payment type seed/sync for SumUp connected (replacing stripe_terminal)."""

from datetime import UTC, datetime

from app.database import SessionLocal, _seed_payment_types, _sync_payment_types_for_sumup
from app.event_sales import PAYMENT_TYPE_LABELS, payment_type_label
from app.models import Event, HireCompany, Organisation, PaymentType
from app.payment_types_config import (
    FALLBACK_PAYMENT_TYPE_ORDER,
    FALLBACK_PAYMENT_TYPES,
    refresh_payment_types_cache,
)


def test_fallback_allowlist_has_sumup_connected_not_stripe_terminal():
    assert "sumup_connected" in FALLBACK_PAYMENT_TYPES
    assert "sumup" in FALLBACK_PAYMENT_TYPES
    assert "stripe_terminal" not in FALLBACK_PAYMENT_TYPES
    assert FALLBACK_PAYMENT_TYPE_ORDER == ("cash", "twint", "sumup", "sumup_connected")


def test_payment_type_labels_manual_and_connected():
    assert payment_type_label("sumup") == "Sumup (manual)"
    assert payment_type_label("sumup_connected") == "Sumup connected"
    assert "sumup_connected" in PAYMENT_TYPE_LABELS
    # Historical stripe rows remain readable
    assert payment_type_label("stripe_terminal") == "Karte (Stripe Terminal)"


def test_sync_activates_sumup_connected_and_deactivates_stripe_terminal():
    db = SessionLocal()
    try:
        # Simulate pre-migration seed
        if db.query(PaymentType).filter(PaymentType.slug == "cash").first() is None:
            for slug, sort_order in (("cash", 0), ("twint", 1), ("sumup", 2), ("stripe_terminal", 3)):
                db.add(PaymentType(slug=slug, sort_order=sort_order, is_active=True))
            db.commit()
        else:
            st = db.query(PaymentType).filter(PaymentType.slug == "stripe_terminal").first()
            if st is None:
                db.add(PaymentType(slug="stripe_terminal", sort_order=3, is_active=True))
            else:
                st.is_active = True
            sc = db.query(PaymentType).filter(PaymentType.slug == "sumup_connected").first()
            if sc is not None:
                db.delete(sc)
            db.commit()
    finally:
        db.close()

    _sync_payment_types_for_sumup()
    _seed_payment_types()

    db = SessionLocal()
    try:
        connected = db.query(PaymentType).filter(PaymentType.slug == "sumup_connected").first()
        assert connected is not None
        assert connected.is_active is True
        stripe = db.query(PaymentType).filter(PaymentType.slug == "stripe_terminal").first()
        if stripe is not None:
            assert stripe.is_active is False
        refresh_payment_types_cache(db)
    finally:
        db.close()

    from app.payment_types_config import allowed_payment_type_slugs

    assert "sumup_connected" in allowed_payment_type_slugs()
    assert "stripe_terminal" not in allowed_payment_type_slugs()


def test_sync_migrates_events_with_only_stripe_terminal():
    db = SessionLocal()
    try:
        hc = HireCompany(name="SumUp Mig HC", country_id=1)
        db.add(hc)
        db.flush()
        org = Organisation(name="SumUp Mig Org", hire_company_id=hc.id, country_id=1, currency="CHF")
        db.add(org)
        db.flush()
        now = datetime.now(UTC)
        event = Event(
            name="SumUp Mig Event",
            status="config",
            start=now,
            end=now,
            organisation_id=org.id,
            payment_types=["stripe_terminal"],
        )
        db.add(event)
        db.commit()
        event_id = event.id
    finally:
        db.close()

    _sync_payment_types_for_sumup()

    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        assert event is not None
        assert "sumup_connected" in (event.payment_types or [])
        assert "stripe_terminal" not in (event.payment_types or [])
    finally:
        db.close()
