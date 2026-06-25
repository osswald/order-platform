import uuid as uuid_lib

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base

organisation_users = Table(
    "organisation_users",
    Base.metadata,
    Column("organisation_id", Integer, ForeignKey("organisations.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
)


class Country(Base):
    __tablename__ = "countries"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(2), unique=True, nullable=False)
    name = Column(String, unique=True, nullable=False)

    organisations = relationship("Organisation", back_populates="country")
    hire_companies = relationship("HireCompany", back_populates="country")
    tax_codes = relationship("TaxCode", back_populates="country")


class HireCompany(Base):
    __tablename__ = "hire_companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    zip = Column(String, nullable=True)
    city = Column(String, nullable=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=True, index=True)
    receipt_printing_config = Column(JSON, nullable=True)
    receipt_logo_mime = Column(String(64), nullable=True)
    receipt_logo_data = Column(Text, nullable=True)
    organisations = relationship("Organisation", back_populates="hire_company")
    appliances = relationship("Appliance", back_populates="hire_company")
    users = relationship("User", back_populates="hire_company", foreign_keys="User.hire_company_id")
    country = relationship("Country", back_populates="hire_companies")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(String(32), nullable=False, default="member")
    hire_company_id = Column(Integer, ForeignKey("hire_companies.id"), nullable=True, index=True)
    event_admin_pin_hash = Column(String(255), nullable=True)
    token_version = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    hire_company = relationship("HireCompany", back_populates="users", foreign_keys=[hire_company_id])
    organisations = relationship("Organisation", secondary=organisation_users, back_populates="users")


class Organisation(Base):
    __tablename__ = "organisations"
    id = Column(Integer, primary_key=True, index=True)
    hire_company_id = Column(Integer, ForeignKey("hire_companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    zip = Column(String, nullable=True)
    city = Column(String, nullable=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False, index=True)
    currency = Column(String(3), nullable=False, default="EUR")
    stripe_account_id = Column(String(255), nullable=True, unique=True, index=True)
    stripe_charges_enabled = Column(Boolean, nullable=False, default=False)
    stripe_payouts_enabled = Column(Boolean, nullable=False, default=False)
    stripe_details_submitted = Column(Boolean, nullable=False, default=False)
    stripe_onboarding_started_at = Column(DateTime(timezone=True), nullable=True)
    stripe_account_updated_at = Column(DateTime(timezone=True), nullable=True)
    receipt_printing_config = Column(JSON, nullable=True)
    receipt_logo_mime = Column(String(64), nullable=True)
    receipt_logo_data = Column(Text, nullable=True)
    vat_liable = Column(Boolean, nullable=False, default=False)
    default_tax_code_id = Column(Integer, ForeignKey("tax_codes.id"), nullable=True, index=True)
    accounts_enabled = Column(Boolean, nullable=False, default=False)
    position_comments_enabled = Column(Boolean, nullable=False, default=False)
    hire_company = relationship("HireCompany", back_populates="organisations")
    country = relationship("Country", back_populates="organisations")
    default_tax_code = relationship("TaxCode", foreign_keys=[default_tax_code_id])
    users = relationship("User", secondary=organisation_users, back_populates="organisations")
    events = relationship("Event", back_populates="organisation", cascade="all, delete-orphan")
    waiters = relationship("Waiter", back_populates="organisation", cascade="all, delete-orphan")
    article_categories = relationship("ArticleCategory", back_populates="organisation", cascade="all, delete-orphan")
    appliance_lendings = relationship("ApplianceLending", back_populates="organisation", cascade="all, delete-orphan")
    position_comment_presets = relationship(
        "OrganisationPositionComment",
        back_populates="organisation",
        cascade="all, delete-orphan",
        order_by="OrganisationPositionComment.sort_order",
    )


class OrganisationPositionComment(Base):
    __tablename__ = "organisation_position_comments"

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    text = Column(String(512), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    organisation = relationship("Organisation", back_populates="position_comment_presets")


class Appliance(Base):
    __tablename__ = "appliances"
    id = Column(Integer, primary_key=True, index=True)
    hire_company_id = Column(Integer, ForeignKey("hire_companies.id"), nullable=False, index=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    escpos_feed_lines = Column(Integer, nullable=True)
    is_hosted_virtual = Column(Boolean, nullable=False, default=False)
    model = Column(String, nullable=True)
    comment = Column(String, nullable=True)
    hire_company = relationship("HireCompany", back_populates="appliances")
    lendings = relationship("ApplianceLending", back_populates="appliance", cascade="all, delete-orphan")
    pairing_sessions = relationship("AppliancePairingSession", back_populates="appliance", cascade="all, delete-orphan")
    edge_credentials = relationship("ApplianceEdgeCredential", back_populates="appliance", cascade="all, delete-orphan")


class ApplianceLending(Base):
    """Lend an appliance to an organisation for an inclusive calendar date range. Dates use server calendar days (UTC)."""

    __tablename__ = "appliance_lendings"
    id = Column(Integer, primary_key=True, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=False)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    returned_at = Column(DateTime(timezone=True), nullable=True)
    appliance = relationship("Appliance", back_populates="lendings")
    organisation = relationship("Organisation", back_populates="appliance_lendings")


class AppliancePairingSession(Base):
    """Short-lived one-time code used by an unpaired Raspberry Pi to obtain edge credentials."""

    __tablename__ = "appliance_pairing_sessions"
    id = Column(Integer, primary_key=True, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    appliance = relationship("Appliance", back_populates="pairing_sessions")
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class ApplianceEdgeCredential(Base):
    """One credentialed SD-card/Pi installation for a server appliance."""

    __tablename__ = "appliance_edge_credentials"
    id = Column(Integer, primary_key=True, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(255), nullable=True)
    edge_client_id = Column(String(64), nullable=False, unique=True, index=True)
    edge_secret_hash = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    appliance = relationship("Appliance", back_populates="edge_credentials")


class HostedPiInstance(Base):
    """Ephemeral cloud-hosted Pi sandbox for a config-status event."""

    __tablename__ = "hosted_pi_instances"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    hire_company_id = Column(Integer, ForeignKey("hire_companies.id", ondelete="CASCADE"), nullable=False, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id", ondelete="SET NULL"), nullable=True, index=True)
    edge_credential_id = Column(Integer, ForeignKey("appliance_edge_credentials.id", ondelete="SET NULL"), nullable=True)
    subdomain_slug = Column(String(32), nullable=False, unique=True, index=True)
    status = Column(String(32), nullable=False, default="provisioning")
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    event = relationship("Event")
    organisation = relationship("Organisation")
    appliance = relationship("Appliance")
    edge_credential = relationship("ApplianceEdgeCredential")
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    start = Column(DateTime(timezone=True), nullable=False)
    end = Column(DateTime(timezone=True), nullable=False)
    # Edge / waiter POS: instant = mark paid on submit; pay_now = pay before submit completes; pay_later = pay after submit.
    payment_mode = Column(String(32), nullable=False, default="pay_later")
    instant_collective_bill_name = Column(String(128), nullable=True)
    instant_collective_bill_uuid = Column(String(36), nullable=True, index=True)
    payment_types = Column(JSON, nullable=False, default=lambda: ["cash"])
    twint_qr_mime = Column(String(64), nullable=True)
    twint_qr_data = Column(String, nullable=True)  # base64-encoded PNG/SVG
    cash_registers_enabled = Column(Boolean, nullable=False, default=False)
    shift_settlement_enabled = Column(Boolean, nullable=False, default=False)
    vouchers_enabled = Column(Boolean, nullable=False, default=False)
    discounts_enabled = Column(Boolean, nullable=False, default=False)
    alternative_printers_enabled = Column(Boolean, nullable=False, default=False)
    kitchen_monitors_enabled = Column(Boolean, nullable=False, default=False)
    offer_payment_receipt = Column(Boolean, nullable=False, default=False)
    receipt_printing_config = Column(JSON, nullable=True)
    receipt_logo_mime = Column(String(64), nullable=True)
    receipt_logo_data = Column(Text, nullable=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    organisation = relationship("Organisation", back_populates="events")
    stations = relationship(
        "EventStation",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventStation.sort_order",
    )
    event_waiters = relationship("EventWaiter", back_populates="event", cascade="all, delete-orphan")
    app_layouts = relationship("EventAppLayout", back_populates="event", cascade="all, delete-orphan")
    cash_registers = relationship(
        "EventCashRegister",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventCashRegister.sort_order",
    )
    voucher_definitions = relationship(
        "EventVoucherDefinition",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventVoucherDefinition.sort_order",
    )
    kitchen_monitor_printers = relationship(
        "EventKitchenMonitorPrinter",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventKitchenMonitorPrinter.sort_order",
    )


class Waiter(Base):
    __tablename__ = "waiters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    pin = Column(String, nullable=False, default="0000")
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    organisation = relationship("Organisation", back_populates="waiters")


class PaymentType(Base):
    __tablename__ = "payment_types"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(32), nullable=False, unique=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AccountingAccount(Base):
    __tablename__ = "accounting_accounts"
    __table_args__ = (
        UniqueConstraint("organisation_id", "number", name="uq_accounting_account_org_number"),
    )

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    number = Column(String, nullable=False)
    is_default_for_article_categories = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    organisation = relationship("Organisation", backref="accounting_accounts")
    payment_type_defaults = relationship(
        "AccountingAccountPaymentTypeDefault",
        back_populates="accounting_account",
        cascade="all, delete-orphan",
    )


class AccountingAccountPaymentTypeDefault(Base):
    __tablename__ = "accounting_account_payment_type_defaults"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "payment_type_id",
            name="uq_org_payment_type_default_account",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    payment_type_id = Column(Integer, ForeignKey("payment_types.id"), nullable=False, index=True)
    accounting_account_id = Column(
        Integer, ForeignKey("accounting_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organisation = relationship("Organisation", backref="payment_type_account_defaults")
    payment_type = relationship("PaymentType")
    accounting_account = relationship("AccountingAccount", back_populates="payment_type_defaults")


class AccountingAccountTaxCodeDefault(Base):
    __tablename__ = "accounting_account_tax_code_defaults"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "tax_code_id",
            name="uq_org_tax_code_default_account",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    tax_code_id = Column(Integer, ForeignKey("tax_codes.id"), nullable=False, index=True)
    accounting_account_id = Column(
        Integer, ForeignKey("accounting_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organisation = relationship("Organisation", backref="tax_code_account_defaults")
    tax_code = relationship("TaxCode")
    accounting_account = relationship("AccountingAccount")


class ArticleCategory(Base):
    __tablename__ = "article_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    accounting_account_id = Column(
        Integer, ForeignKey("accounting_accounts.id"), nullable=True, index=True
    )
    organisation = relationship("Organisation", back_populates="article_categories")
    accounting_account = relationship("AccountingAccount", foreign_keys=[accounting_account_id])
    articles = relationship("Article", back_populates="article_category")


event_station_articles = Table(
    "event_station_articles",
    Base.metadata,
    Column("station_id", Integer, ForeignKey("event_stations.id", ondelete="CASCADE"), primary_key=True),
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
)

event_app_layout_cell_articles = Table(
    "event_app_layout_cell_articles",
    Base.metadata,
    Column("cell_id", Integer, ForeignKey("event_app_layout_cells.id", ondelete="CASCADE"), primary_key=True),
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
)


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    label = Column(String(22), nullable=False)
    price = Column(Float, nullable=False)
    import_article_number = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    unit = Column(String, nullable=True)
    accounting_account_id = Column(
        Integer, ForeignKey("accounting_accounts.id"), nullable=True, index=True
    )
    tax_code_id = Column(Integer, ForeignKey("tax_codes.id"), nullable=True, index=True)
    is_addition = Column(Boolean, nullable=False, default=False)
    article_category_id = Column(Integer, ForeignKey("article_categories.id"), nullable=False)
    article_category = relationship("ArticleCategory", back_populates="articles")
    accounting_account = relationship("AccountingAccount", foreign_keys=[accounting_account_id])
    tax_code = relationship("TaxCode", foreign_keys=[tax_code_id])
    event_stations = relationship(
        "EventStation",
        secondary=event_station_articles,
        back_populates="articles",
    )


class ArticleAdditionLink(Base):
    """Which Zusatz articles can be selected for a base article."""

    __tablename__ = "article_addition_links"
    base_article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    addition_article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    sort_order = Column(Integer, nullable=False, default=0)
    base_article = relationship("Article", foreign_keys=[base_article_id])
    addition_article = relationship("Article", foreign_keys=[addition_article_id])


class EventStation(Base):
    __tablename__ = "event_stations"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid_lib.uuid4()),
    )
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    printer_appliance_id = Column(Integer, ForeignKey("appliances.id", ondelete="SET NULL"), nullable=True)
    kitchen_monitor_enabled = Column(Boolean, nullable=False, default=False)
    event = relationship("Event", back_populates="stations")
    printer_appliance = relationship("Appliance", foreign_keys=[printer_appliance_id])
    articles = relationship(
        "Article",
        secondary=event_station_articles,
        back_populates="event_stations",
    )
    printer_rules = relationship(
        "EventStationPrinterRule",
        back_populates="station",
        cascade="all, delete-orphan",
        order_by="EventStationPrinterRule.sort_order",
    )


class EventStationPrinterRule(Base):
    __tablename__ = "event_station_printer_rules"
    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("event_stations.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    rule_type = Column(String(32), nullable=False)
    table_from = Column(Integer, nullable=True)
    table_to = Column(Integer, nullable=True)
    pickup_prefix = Column(String(3), nullable=True)
    printer_appliance_id = Column(Integer, ForeignKey("appliances.id", ondelete="SET NULL"), nullable=True)
    station = relationship("EventStation", back_populates="printer_rules")
    printer_appliance = relationship("Appliance", foreign_keys=[printer_appliance_id])


class EventKitchenMonitorPrinter(Base):
    __tablename__ = "event_kitchen_monitor_printers"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    printer_appliance_id = Column(Integer, ForeignKey("appliances.id", ondelete="CASCADE"), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    label = Column(String(128), nullable=True)
    event = relationship("Event", back_populates="kitchen_monitor_printers")
    printer_appliance = relationship("Appliance", foreign_keys=[printer_appliance_id])


class EventWaiter(Base):
    __tablename__ = "event_waiters"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid_lib.uuid4()),
    )
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    pin = Column(String, nullable=False, default="0000")
    subsidiary_code = Column(String(32), nullable=True)
    source_waiter_id = Column(Integer, ForeignKey("waiters.id", ondelete="SET NULL"), nullable=True)
    event = relationship("Event", back_populates="event_waiters")
    source_waiter = relationship("Waiter", foreign_keys=[source_waiter_id])


class EventAppLayout(Base):
    __tablename__ = "event_app_layouts"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid_lib.uuid4()),
    )
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    grid_width = Column(Integer, nullable=False)
    grid_height = Column(Integer, nullable=False)
    event = relationship("Event", back_populates="app_layouts")
    cells = relationship(
        "EventAppLayoutCell",
        back_populates="layout",
        cascade="all, delete-orphan",
    )


class EventCashRegister(Base):
    __tablename__ = "event_cash_registers"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid_lib.uuid4()),
    )
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    pickup_code_prefix = Column(String(3), nullable=False)
    pin = Column(String, nullable=False, default="0000")
    subsidiary_code = Column(String(32), nullable=True)
    layout_uuid = Column(String(36), nullable=False)
    receipt_printer_appliance_id = Column(Integer, ForeignKey("appliances.id", ondelete="SET NULL"), nullable=True)
    event = relationship("Event", back_populates="cash_registers")
    receipt_printer_appliance = relationship("Appliance", foreign_keys=[receipt_printer_appliance_id])


class EventCollectiveBill(Base):
    """Sammelrechnung header synced from Pi edge payloads."""

    __tablename__ = "event_collective_bills"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), nullable=False, unique=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    event = relationship("Event", backref="collective_bills")


class EdgeSubmittedOrder(Base):
    """Orders submitted from on-prem Pi (idempotent by client_order_id)."""

    __tablename__ = "edge_submitted_orders"
    id = Column(Integer, primary_key=True, index=True)
    client_order_id = Column(String(64), nullable=False, unique=True, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=False)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EventVoucherDefinition(Base):
    __tablename__ = "event_voucher_definitions"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid_lib.uuid4()),
    )
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    kind = Column(String(32), nullable=False)  # fixed_amount | article_entitlement
    value_cents = Column(Integer, nullable=True)
    allowed_article_ids = Column(JSON, nullable=False, default=list)
    include_additions = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    event = relationship("Event", back_populates="voucher_definitions")


class EventVoucherRedemption(Base):
    """Audit row when a voucher type is redeemed at payment (synced from Pi)."""

    __tablename__ = "event_voucher_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid_lib.uuid4()),
    )
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    voucher_definition_uuid = Column(String(36), nullable=False, index=True)
    payment_client_order_id = Column(String(64), nullable=False, index=True)
    kind = Column(String(32), nullable=False)
    applied_cents = Column(Integer, nullable=False, default=0)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="SET NULL"), nullable=True)
    note = Column(String, nullable=True)
    additions = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    event = relationship("Event", backref="voucher_redemptions")


class EventAppLayoutCell(Base):
    __tablename__ = "event_app_layout_cells"
    __table_args__ = (UniqueConstraint("layout_id", "row", "col", name="uq_event_app_layout_cell_pos"),)

    id = Column(Integer, primary_key=True, index=True)
    layout_id = Column(Integer, ForeignKey("event_app_layouts.id", ondelete="CASCADE"), nullable=False)
    row = Column(Integer, nullable=False)
    col = Column(Integer, nullable=False)
    label = Column(String, nullable=False, default="")
    color = Column(String, nullable=False, default="#eeeeee")
    voucher_definition_uuid = Column(String(36), nullable=True)
    voucher_definition_uuids = Column(JSON, nullable=False, default=list)
    layout = relationship("EventAppLayout", back_populates="cells")
    articles = relationship(
        "Article",
        secondary=event_app_layout_cell_articles,
    )


class EventArticleStock(Base):
    """Per-event stock overrides for articles linked to event stations."""

    __tablename__ = "event_article_stock"
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    monitor_stock = Column(Boolean, nullable=False, default=False)
    in_stock = Column(Integer, nullable=True)
    baseline_in_stock = Column(Integer, nullable=True)
    event = relationship("Event", backref="article_stock")
    article = relationship("Article")


class EdgeOrderSession(Base):
    __tablename__ = "edge_order_sessions"
    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    session_id = Column(Integer, nullable=False, index=True)
    table_number = Column(Integer, nullable=True, index=True)
    order_source = Column(String(32), nullable=False, default="waiter")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EdgeOrderItem(Base):
    __tablename__ = "edge_order_items"
    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    session_id = Column(Integer, nullable=False, index=True)
    submission_id = Column(Integer, nullable=True, index=True)
    article_id = Column(Integer, nullable=True, index=True)
    article_name = Column(String(255), nullable=False, default="")
    station_uuid = Column(String(36), nullable=True, index=True)
    waiter_uuid = Column(String(36), nullable=True, index=True)
    cash_register_uuid = Column(String(36), nullable=True, index=True)
    order_source = Column(String(32), nullable=True, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price_cents = Column(Integer, nullable=False, default=0)
    line_total_cents = Column(Integer, nullable=False, default=0)
    tax_code_id = Column(Integer, nullable=True, index=True)
    tax_rate_percent = Column(Float, nullable=True)
    accounting_account_id = Column(Integer, nullable=True, index=True)
    net_cents = Column(Integer, nullable=True)
    vat_cents = Column(Integer, nullable=True)
    payment_status = Column(String(16), nullable=False, default="open")
    payment_batch_uuid = Column(String(36), nullable=True, index=True)
    method = Column(String(32), nullable=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EdgePaymentBatch(Base):
    __tablename__ = "edge_payment_batches"
    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    batch_uuid = Column(String(36), nullable=False, index=True)
    name = Column(String(128), nullable=False, default="Sammelrechnung")
    status = Column(String(16), nullable=False, default="open")
    total_cents = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)


class EdgeOrderSnapshot(Base):
    """Latest open order payload per org/event for Pi restore."""

    __tablename__ = "edge_order_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "event_id",
            "logical_client_order_id",
            name="uq_edge_order_snapshot_logical",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    logical_client_order_id = Column(String(64), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EdgeKitchenTicketSnapshot(Base):
    """Kitchen monitor state per order for Pi restore."""

    __tablename__ = "edge_kitchen_ticket_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "event_id",
            "logical_client_order_id",
            name="uq_edge_kitchen_snapshot_logical",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    logical_client_order_id = Column(String(64), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EdgeCashSession(Base):
    __tablename__ = "edge_cash_sessions"
    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    subject_key = Column(String(128), nullable=True, index=True)
    cash_session_id = Column(Integer, nullable=False, index=True)
    subject_type = Column(String(32), nullable=False, default="waiter")
    waiter_uuid = Column(String(36), nullable=True, index=True)
    cash_register_uuid = Column(String(36), nullable=True, index=True)
    subject_name = Column(String(128), nullable=False, default="")
    operator_waiter_uuid = Column(String(36), nullable=True)
    status = Column(String(16), nullable=False, default="OPEN")
    opening_balance_cents = Column(Integer, nullable=False, default=0)
    wallet_cents = Column(Integer, nullable=False, default=0)
    total_cash_cents = Column(Integer, nullable=False, default=0)
    total_non_cash_cents = Column(Integer, nullable=False, default=0)
    counted_cash_cents = Column(Integer, nullable=True)
    variance_cents = Column(Integer, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EdgePayment(Base):
    __tablename__ = "edge_payments"
    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    submission_id = Column(Integer, nullable=True, index=True)
    payment_batch_uuid = Column(String(36), nullable=True, index=True)
    method = Column(String(32), nullable=False, default="cash")
    amount_cents = Column(Integer, nullable=False, default=0)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TaxCode(Base):
    __tablename__ = "tax_codes"
    __table_args__ = (UniqueConstraint("country_id", "name", name="uq_tax_code_country_name"),)

    id = Column(Integer, primary_key=True, index=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    country = relationship("Country", back_populates="tax_codes")
    rates = relationship(
        "TaxCodeRate",
        back_populates="tax_code",
        cascade="all, delete-orphan",
        order_by="TaxCodeRate.valid_from",
    )


class TaxCodeRate(Base):
    __tablename__ = "tax_code_rates"

    id = Column(Integer, primary_key=True, index=True)
    tax_code_id = Column(Integer, ForeignKey("tax_codes.id", ondelete="CASCADE"), nullable=False, index=True)
    rate_percent = Column(Float, nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    tax_code = relationship("TaxCode", back_populates="rates")


class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    stripe_event_id = Column(String(255), nullable=False, unique=True, index=True)
    event_type = Column(String(128), nullable=False)
    payment_intent_id = Column(String(255), nullable=True, index=True)
    metadata_json = Column(JSON, nullable=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
