"""Backfill home Verleiher (hire_company_id) for members / organisation-admins."""

from app.database import SessionLocal, _backfill_user_home_verleiher, engine
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_MEMBER, ROLE_ORGANISATION_ADMIN, ROLE_PLATFORM_ADMIN
from app.security import get_password_hash
from sqlalchemy import text

from tests.helpers import country_id_by_code


def test_backfill_user_home_verleiher_from_single_org():
    db = SessionLocal()
    try:
        hc = HireCompany(name="Backfill HC")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="Backfill Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        member = User(
            email="backfill-member@example.com",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
            hire_company_id=None,
        )
        member.organisations = [org]
        oa = User(
            email="backfill-oa@example.com",
            hashed_password=get_password_hash("secret"),
            role=ROLE_ORGANISATION_ADMIN,
            hire_company_id=None,
        )
        oa.organisations = [org]
        platform = User(
            email="backfill-platform@example.com",
            hashed_password=get_password_hash("secret"),
            role=ROLE_PLATFORM_ADMIN,
            is_superuser=True,
            hire_company_id=None,
        )
        orphan = User(
            email="backfill-orphan@example.com",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
            hire_company_id=None,
        )
        db.add_all([member, oa, platform, orphan])
        db.commit()
        member_id, oa_id, platform_id, orphan_id = member.id, oa.id, platform.id, orphan.id
        hc_id = hc.id
    finally:
        db.close()

    _backfill_user_home_verleiher()

    db = SessionLocal()
    try:
        assert db.get(User, member_id).hire_company_id == hc_id
        assert db.get(User, oa_id).hire_company_id == hc_id
        assert db.get(User, platform_id).hire_company_id is None
        assert db.get(User, orphan_id).hire_company_id is None
    finally:
        db.close()


def test_backfill_user_home_verleiher_skips_ambiguous_multi_verleiher_orgs():
    db = SessionLocal()
    try:
        hc_a = HireCompany(name="Ambiguous A")
        hc_b = HireCompany(name="Ambiguous B")
        db.add_all([hc_a, hc_b])
        db.flush()
        org_a = Organisation(
            name="Ambiguous Org A",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc_a.id,
            currency="CHF",
        )
        org_b = Organisation(
            name="Ambiguous Org B",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc_b.id,
            currency="CHF",
        )
        db.add_all([org_a, org_b])
        db.flush()
        member = User(
            email="backfill-ambiguous@example.com",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
            hire_company_id=None,
        )
        member.organisations = [org_a, org_b]
        db.add(member)
        db.commit()
        member_id = member.id
    finally:
        db.close()

    _backfill_user_home_verleiher()

    db = SessionLocal()
    try:
        assert db.get(User, member_id).hire_company_id is None
    finally:
        db.close()


def test_backfill_user_home_verleiher_is_idempotent():
    db = SessionLocal()
    try:
        hc = HireCompany(name="Idempotent HC")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="Idempotent Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        member = User(
            email="backfill-idempotent@example.com",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
            hire_company_id=None,
        )
        member.organisations = [org]
        db.add(member)
        db.commit()
        member_id = member.id
        hc_id = hc.id
    finally:
        db.close()

    _backfill_user_home_verleiher()
    _backfill_user_home_verleiher()

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT hire_company_id FROM users WHERE id = :id"),
            {"id": member_id},
        ).fetchone()
    assert row[0] == hc_id
