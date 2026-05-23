import uuid as uuid_lib

from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Float, Table, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

organisation_users = Table(
    "organisation_users",
    Base.metadata,
    Column("organisation_id", Integer, ForeignKey("organisations.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
)


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    event_admin_pin_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    organisations = relationship("Organisation", secondary=organisation_users, back_populates="users")


class Organisation(Base):
    __tablename__ = "organisations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    zip = Column(String, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=False)
    users = relationship("User", secondary=organisation_users, back_populates="organisations")
    events = relationship("Event", back_populates="organisation", cascade="all, delete-orphan")
    waiters = relationship("Waiter", back_populates="organisation", cascade="all, delete-orphan")
    article_categories = relationship("ArticleCategory", back_populates="organisation", cascade="all, delete-orphan")
    appliance_lendings = relationship("ApplianceLending", back_populates="organisation", cascade="all, delete-orphan")


class Appliance(Base):
    __tablename__ = "appliances"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    model = Column(String, nullable=True)
    comment = Column(String, nullable=True)
    # Raspberry Pi / edge: device authenticates to cloud with client id + secret (secret stored hashed).
    edge_client_id = Column(String(64), nullable=True, unique=True, index=True)
    edge_secret_hash = Column(String(255), nullable=True)
    lendings = relationship("ApplianceLending", back_populates="appliance", cascade="all, delete-orphan")


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


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    start = Column(DateTime(timezone=True), nullable=False)
    end = Column(DateTime(timezone=True), nullable=False)
    currency = Column(String, nullable=False)
    # Edge / waiter POS: instant = mark paid on submit; pay_now = pay before submit completes; pay_later = pay after submit.
    payment_mode = Column(String(32), nullable=False, default="pay_later")
    payment_types = Column(JSON, nullable=False, default=lambda: ["cash"])
    twint_qr_mime = Column(String(64), nullable=True)
    twint_qr_data = Column(String, nullable=True)  # base64-encoded PNG/SVG
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


class Waiter(Base):
    __tablename__ = "waiters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    pin = Column(String, nullable=False, default="0000")
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    organisation = relationship("Organisation", back_populates="waiters")


class ArticleCategory(Base):
    __tablename__ = "article_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    organisation = relationship("Organisation", back_populates="article_categories")
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
    is_addition = Column(Boolean, nullable=False, default=False)
    monitor_stock = Column(Boolean, nullable=False, default=False)
    in_stock = Column(Integer, nullable=True)
    article_category_id = Column(Integer, ForeignKey("article_categories.id"), nullable=False)
    article_category = relationship("ArticleCategory", back_populates="articles")
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
    event = relationship("Event", back_populates="stations")
    printer_appliance = relationship("Appliance", foreign_keys=[printer_appliance_id])
    articles = relationship(
        "Article",
        secondary=event_station_articles,
        back_populates="event_stations",
    )


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
    source_waiter_id = Column(Integer, ForeignKey("waiters.id", ondelete="SET NULL"), nullable=True)
    event = relationship("Event", back_populates="event_waiters")
    source_waiter = relationship("Waiter", foreign_keys=[source_waiter_id])


class EventAppLayout(Base):
    __tablename__ = "event_app_layouts"
    id = Column(Integer, primary_key=True, index=True)
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


class EventAppLayoutCell(Base):
    __tablename__ = "event_app_layout_cells"
    __table_args__ = (UniqueConstraint("layout_id", "row", "col", name="uq_event_app_layout_cell_pos"),)

    id = Column(Integer, primary_key=True, index=True)
    layout_id = Column(Integer, ForeignKey("event_app_layouts.id", ondelete="CASCADE"), nullable=False)
    row = Column(Integer, nullable=False)
    col = Column(Integer, nullable=False)
    label = Column(String, nullable=False, default="")
    color = Column(String, nullable=False, default="#eeeeee")
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
