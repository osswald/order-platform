"""Legacy lendings without rental_id are backfilled one-to-one into rentals."""

from datetime import date

from app.models import Appliance, HireCompany, Organisation
from app.rental_backfill import backfill_appliance_lending_rentals
from sqlalchemy import create_engine, text

from tests.helpers import ensure_country


def test_backfill_creates_one_rental_per_lending_and_leaves_no_null_rental_id():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE hire_companies (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL)"))
        conn.execute(
            text(
                "CREATE TABLE countries (id INTEGER PRIMARY KEY, code VARCHAR(2) NOT NULL, name VARCHAR NOT NULL)"
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE organisations (
                    id INTEGER PRIMARY KEY,
                    hire_company_id INTEGER NOT NULL,
                    name VARCHAR NOT NULL,
                    country_id INTEGER NOT NULL,
                    currency VARCHAR(3) NOT NULL DEFAULT 'EUR'
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE appliances (
                    id INTEGER PRIMARY KEY,
                    hire_company_id INTEGER NOT NULL,
                    type VARCHAR NOT NULL,
                    name VARCHAR,
                    is_hosted_virtual BOOLEAN NOT NULL DEFAULT 0
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE rentals (
                    id INTEGER PRIMARY KEY,
                    hire_company_id INTEGER NOT NULL,
                    organisation_id INTEGER NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    label VARCHAR(255)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE appliance_lendings (
                    id INTEGER PRIMARY KEY,
                    rental_id INTEGER,
                    appliance_id INTEGER NOT NULL,
                    organisation_id INTEGER NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    returned_at DATETIME
                )
                """
            )
        )
        conn.execute(text("INSERT INTO hire_companies (id, name) VALUES (1, 'Tenant')"))
        conn.execute(text("INSERT INTO countries (id, code, name) VALUES (1, 'CH', 'Schweiz')"))
        conn.execute(
            text(
                "INSERT INTO organisations (id, hire_company_id, name, country_id, currency) "
                "VALUES (10, 1, 'Org', 1, 'CHF')"
            )
        )
        conn.execute(
            text("INSERT INTO appliances (id, hire_company_id, type, name) VALUES (20, 1, 'server', 'Pi-01')")
        )
        conn.execute(
            text(
                "INSERT INTO appliance_lendings (id, rental_id, appliance_id, organisation_id, start_date, end_date) "
                "VALUES (30, NULL, 20, 10, '2026-06-12', '2026-06-15')"
            )
        )
        updated = backfill_appliance_lending_rentals(conn)
        assert updated == 1
        leftover = conn.execute(text("SELECT COUNT(*) FROM appliance_lendings WHERE rental_id IS NULL")).scalar()
        assert leftover == 0
        rental = conn.execute(text("SELECT hire_company_id, organisation_id, start_date, end_date, label FROM rentals")).one()
        assert rental[0] == 1
        assert rental[1] == 10
        assert str(rental[2]) == "2026-06-12"
        assert str(rental[3]) == "2026-06-15"
        assert rental[4] is None
        lending_rental_id = conn.execute(text("SELECT rental_id FROM appliance_lendings WHERE id = 30")).scalar()
        assert lending_rental_id == conn.execute(text("SELECT id FROM rentals")).scalar()


def test_orm_lending_requires_rental(memory_db_session):
    db = memory_db_session
    country_id = ensure_country(db, "CH")
    company = HireCompany(name="Rental FK Tenant")
    db.add(company)
    db.flush()
    org = Organisation(
        name="Rental FK Org",
        country_id=country_id,
        hire_company_id=company.id,
        currency="CHF",
    )
    appliance = Appliance(hire_company_id=company.id, type="server", name="Pi")
    db.add_all([org, appliance])
    db.flush()
    from app.models import ApplianceLending

    db.add(
        ApplianceLending(
            appliance_id=appliance.id,
            organisation_id=org.id,
            start_date=date(2026, 6, 12),
            end_date=date(2026, 6, 15),
        )
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
    else:
        raise AssertionError("lending without rental_id should not commit")
    leftover = db.execute(text("SELECT COUNT(*) FROM appliance_lendings WHERE rental_id IS NULL")).scalar()
    assert leftover == 0
