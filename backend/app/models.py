import uuid
from datetime import UTC, date, datetime, time

from pydantic import EmailStr
from sqlalchemy import CheckConstraint, Date, DateTime, Time
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# ============================================================================
# USER & AUTHENTICATION MODELS (Template Core + Extended Role)
# ============================================================================


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    role: str = Field(default="customer", max_length=50, index=True)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = Field(default=None, max_length=50)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class User(UserBase, table=True):
    __tablename__ = "user"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list[Item] = Relationship(back_populates="owner", cascade_delete=True)
    customer_profile: Customer | None = Relationship(back_populates="user")
    technician_profile: Technician | None = Relationship(back_populates="user")


class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# ============================================================================
# TEMPLATE ITEM MODELS (Maintained for backward compatibility)
# ============================================================================


class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class Item(ItemBase, table=True):
    __tablename__ = "item"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# ============================================================================
# FIXPHONE ENTITY: CUSTOMER
# ============================================================================


class CustomerBase(SQLModel):
    full_name: str = Field(max_length=255)
    # Index on phone_number: Critical for fast customer lookups during walk-in or booking calls
    phone_number: str = Field(unique=True, index=True, max_length=20)
    email: EmailStr | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)


class CustomerCreate(CustomerBase):
    user_id: uuid.UUID | None = None


class CustomerUpdate(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)


class Customer(CustomerBase, table=True):
    __tablename__ = "customer"
    __table_args__ = (
        CheckConstraint(
            "length(phone_number) >= 8", name="check_customer_phone_min_length"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # TODO: NEED CONFIRMATION: Can customer exist without user account?
    # Designed as optional FK (nullable=True, SET NULL) to support walk-in guest customers without forced account registration.
    user_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    user: User | None = Relationship(back_populates="customer_profile")
    devices: list[Device] = Relationship(back_populates="customer", cascade_delete=True)
    appointments: list[Appointment] = Relationship(back_populates="customer")
    invoices: list[Invoice] = Relationship(back_populates="customer")
    reviews: list[Review] = Relationship(back_populates="customer")
    notifications: list[Notification] = Relationship(
        back_populates="customer", cascade_delete=True
    )


class CustomerPublic(CustomerBase):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    created_at: datetime | None = None


# ============================================================================
# FIXPHONE ENTITY: DEVICE
# ============================================================================


class DeviceBase(SQLModel):
    device_type: str = Field(default="Smartphone", max_length=50)
    brand: str = Field(max_length=100, index=True)
    model: str = Field(max_length=100, index=True)
    serial_number: str | None = Field(default=None, max_length=100)
    imei: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=500)


class DeviceCreate(DeviceBase):
    customer_id: uuid.UUID


class DeviceUpdate(SQLModel):
    device_type: str | None = Field(default=None, max_length=50)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    imei: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=500)


class Device(DeviceBase, table=True):
    __tablename__ = "device"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    customer_id: uuid.UUID = Field(
        foreign_key="customer.id", ondelete="CASCADE", nullable=False, index=True
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    customer: Customer = Relationship(back_populates="devices")
    appointments: list[Appointment] = Relationship(back_populates="device")


class DevicePublic(DeviceBase):
    id: uuid.UUID
    customer_id: uuid.UUID
    created_at: datetime | None = None


# ============================================================================
# FIXPHONE ENTITY: SERVICE
# ============================================================================


class ServiceBase(SQLModel):
    name: str = Field(unique=True, index=True, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    base_price: float = Field(default=0.0)
    estimated_duration_minutes: int = Field(default=30)
    is_active: bool = Field(default=True, index=True)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    base_price: float | None = None
    estimated_duration_minutes: int | None = None
    is_active: bool | None = None


class Service(ServiceBase, table=True):
    __tablename__ = "service"
    __table_args__ = (
        CheckConstraint(
            "base_price >= 0", name="check_service_base_price_non_negative"
        ),
        CheckConstraint(
            "estimated_duration_minutes > 0", name="check_service_duration_positive"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    appointment_services: list[AppointmentService] = Relationship(
        back_populates="service"
    )


class ServicePublic(ServiceBase):
    id: uuid.UUID
    created_at: datetime | None = None


# ============================================================================
# FIXPHONE ENTITY: TECHNICIAN
# ============================================================================


class TechnicianBase(SQLModel):
    full_name: str = Field(max_length=255)
    phone_number: str | None = Field(default=None, max_length=20, unique=True)
    specialization: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True, index=True)


class TechnicianCreate(TechnicianBase):
    user_id: uuid.UUID | None = None


class TechnicianUpdate(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=20)
    specialization: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class Technician(TechnicianBase, table=True):
    __tablename__ = "technician"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # TODO: NEED CONFIRMATION: Is user account strictly required for every technician or created on-demand?
    # Designed as optional unique FK (nullable=True, SET NULL) to decouple staff profiles from login accounts.
    user_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        nullable=True,
        unique=True,
        index=True,
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    user: User | None = Relationship(back_populates="technician_profile")
    schedules: list[TechnicianSchedule] = Relationship(
        back_populates="technician", cascade_delete=True
    )
    appointments: list[Appointment] = Relationship(back_populates="technician")
    reviews: list[Review] = Relationship(back_populates="technician")


class TechnicianPublic(TechnicianBase):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    created_at: datetime | None = None


# ============================================================================
# FIXPHONE ENTITY: TECHNICIAN SCHEDULE (WORKING SCHEDULE)
# ============================================================================


class TechnicianScheduleBase(SQLModel):
    work_date: date = Field(sa_type=Date, index=True)
    start_time: time = Field(sa_type=Time)
    end_time: time = Field(sa_type=Time)
    status: str = Field(default="AVAILABLE", max_length=50)  # AVAILABLE, BUSY, OFF
    notes: str | None = Field(default=None, max_length=500)


class TechnicianScheduleCreate(TechnicianScheduleBase):
    technician_id: uuid.UUID


class TechnicianScheduleUpdate(SQLModel):
    work_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    status: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=500)


class TechnicianSchedule(TechnicianScheduleBase, table=True):
    __tablename__ = "technician_schedule"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_schedule_time_valid"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    technician_id: uuid.UUID = Field(
        foreign_key="technician.id", ondelete="CASCADE", nullable=False, index=True
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    technician: Technician = Relationship(back_populates="schedules")


class TechnicianSchedulePublic(TechnicianScheduleBase):
    id: uuid.UUID
    technician_id: uuid.UUID
    created_at: datetime | None = None


# ============================================================================
# FIXPHONE ENTITY: APPOINTMENT / REPAIR ORDER
# ============================================================================


class AppointmentBase(SQLModel):
    # Unique appointment tracking code for customer status checking (e.g. APPT-2026-0001)
    appointment_number: str = Field(unique=True, index=True, max_length=50)
    # Index on appointment_date: Essential for filtering schedule by day/week/month
    appointment_date: datetime = Field(sa_type=DateTime(timezone=True), index=True)  # type: ignore
    # Index on status: Filter appointments by PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    status: str = Field(default="PENDING", max_length=50, index=True)
    cancellation_reason: str | None = Field(default=None, max_length=500)
    customer_notes: str | None = Field(default=None, max_length=1000)
    technician_diagnosis: str | None = Field(default=None, max_length=1000)
    estimated_completion_date: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)  # type: ignore
    )
    actual_completion_date: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)  # type: ignore
    )
    total_amount: float = Field(default=0.0)


class AppointmentCreate(AppointmentBase):
    customer_id: uuid.UUID
    device_id: uuid.UUID
    technician_id: uuid.UUID | None = None


class AppointmentUpdate(SQLModel):
    technician_id: uuid.UUID | None = None
    appointment_date: datetime | None = None
    status: str | None = Field(default=None, max_length=50)
    cancellation_reason: str | None = Field(default=None, max_length=500)
    customer_notes: str | None = Field(default=None, max_length=1000)
    technician_diagnosis: str | None = Field(default=None, max_length=1000)
    estimated_completion_date: datetime | None = None
    actual_completion_date: datetime | None = None
    total_amount: float | None = None


class Appointment(AppointmentBase, table=True):
    __tablename__ = "appointment"
    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0", name="check_appointment_total_amount_non_negative"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Foreign key RESTRICT: Protect historical repair data from accidental customer/device deletion
    customer_id: uuid.UUID = Field(
        foreign_key="customer.id", ondelete="RESTRICT", nullable=False, index=True
    )
    device_id: uuid.UUID = Field(
        foreign_key="device.id", ondelete="RESTRICT", nullable=False, index=True
    )
    technician_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="technician.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    customer: Customer = Relationship(back_populates="appointments")
    device: Device = Relationship(back_populates="appointments")
    technician: Technician | None = Relationship(back_populates="appointments")
    services: list[AppointmentService] = Relationship(
        back_populates="appointment", cascade_delete=True
    )
    status_history: list[RepairStatusHistory] = Relationship(
        back_populates="appointment", cascade_delete=True
    )
    quotes: list[Quote] = Relationship(back_populates="appointment")
    invoice: Invoice | None = Relationship(back_populates="appointment")
    review: Review | None = Relationship(back_populates="appointment")


class AppointmentPublic(AppointmentBase):
    id: uuid.UUID
    customer_id: uuid.UUID
    device_id: uuid.UUID
    technician_id: uuid.UUID | None = None
    created_at: datetime | None = None


# ============================================================================
# FIXPHONE ENTITY: APPOINTMENT SERVICE LINK (Many-to-Many + Historical Snapshot)
# ============================================================================


class AppointmentServiceBase(SQLModel):
    # Snapshot of service price at booking time to preserve historical financial accuracy
    price_at_booking: float = Field(nullable=False)
    quantity: int = Field(default=1)
    notes: str | None = Field(default=None, max_length=500)


class AppointmentServiceCreate(AppointmentServiceBase):
    appointment_id: uuid.UUID
    service_id: uuid.UUID


class AppointmentService(AppointmentServiceBase, table=True):
    __tablename__ = "appointment_service"
    __table_args__ = (
        CheckConstraint(
            "price_at_booking >= 0", name="check_appointment_service_price_non_negative"
        ),
        CheckConstraint(
            "quantity > 0", name="check_appointment_service_quantity_positive"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    appointment_id: uuid.UUID = Field(
        foreign_key="appointment.id", ondelete="CASCADE", nullable=False, index=True
    )
    service_id: uuid.UUID = Field(
        foreign_key="service.id", ondelete="RESTRICT", nullable=False, index=True
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    appointment: Appointment = Relationship(back_populates="services")
    service: Service = Relationship(back_populates="appointment_services")


class AppointmentServicePublic(AppointmentServiceBase):
    id: uuid.UUID
    appointment_id: uuid.UUID
    service_id: uuid.UUID


# ============================================================================
# FIXPHONE ENTITY: REPAIR STATUS HISTORY (Audit Trail)
# ============================================================================


class RepairStatusHistoryBase(SQLModel):
    previous_status: str | None = Field(default=None, max_length=50)
    new_status: str = Field(max_length=50, index=True)
    note: str | None = Field(default=None, max_length=1000)


class RepairStatusHistoryCreate(RepairStatusHistoryBase):
    appointment_id: uuid.UUID
    changed_by_user_id: uuid.UUID | None = None


class RepairStatusHistory(RepairStatusHistoryBase, table=True):
    __tablename__ = "repair_status_history"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Index on appointment_id: Essential for pulling the full status timeline of a repair order
    appointment_id: uuid.UUID = Field(
        foreign_key="appointment.id", ondelete="CASCADE", nullable=False, index=True
    )
    changed_by_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )

    appointment: Appointment = Relationship(back_populates="status_history")
    changed_by: User | None = Relationship()


class RepairStatusHistoryPublic(RepairStatusHistoryBase):
    id: uuid.UUID
    appointment_id: uuid.UUID
    changed_by_user_id: uuid.UUID | None = None
    created_at: datetime | None = None


# ============================================================================
# FIXPHONE ENTITY: QUOTE & QUOTE ITEM
# ============================================================================


class QuoteBase(SQLModel):
    quote_number: str = Field(unique=True, index=True, max_length=50)  # QUO-2026-0001
    total_amount: float = Field(default=0.0)
    status: str = Field(
        default="DRAFT", max_length=50, index=True
    )  # DRAFT, SENT, ACCEPTED, REJECTED
    valid_until: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    customer_notes: str | None = Field(default=None, max_length=1000)


class QuoteCreate(QuoteBase):
    appointment_id: uuid.UUID


class QuoteUpdate(SQLModel):
    total_amount: float | None = None
    status: str | None = Field(default=None, max_length=50)
    valid_until: datetime | None = None
    customer_notes: str | None = Field(default=None, max_length=1000)


class Quote(QuoteBase, table=True):
    __tablename__ = "quote"
    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0", name="check_quote_total_amount_non_negative"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    appointment_id: uuid.UUID = Field(
        foreign_key="appointment.id", ondelete="RESTRICT", nullable=False, index=True
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    appointment: Appointment = Relationship(back_populates="quotes")
    items: list[QuoteItem] = Relationship(back_populates="quote", cascade_delete=True)


class QuotePublic(QuoteBase):
    id: uuid.UUID
    appointment_id: uuid.UUID
    created_at: datetime | None = None


class QuoteItemBase(SQLModel):
    item_name: str = Field(max_length=255)
    unit_price: float = Field(default=0.0)
    quantity: int = Field(default=1)
    total_price: float = Field(default=0.0)
    notes: str | None = Field(default=None, max_length=500)


class QuoteItemCreate(QuoteItemBase):
    quote_id: uuid.UUID
    service_id: uuid.UUID | None = None


class QuoteItem(QuoteItemBase, table=True):
    __tablename__ = "quote_item"
    __table_args__ = (
        CheckConstraint(
            "unit_price >= 0", name="check_quote_item_unit_price_non_negative"
        ),
        CheckConstraint("quantity > 0", name="check_quote_item_quantity_positive"),
        CheckConstraint(
            "total_price >= 0", name="check_quote_item_total_price_non_negative"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quote_id: uuid.UUID = Field(
        foreign_key="quote.id", ondelete="CASCADE", nullable=False, index=True
    )
    service_id: uuid.UUID | None = Field(
        default=None, foreign_key="service.id", ondelete="SET NULL", nullable=True
    )

    quote: Quote = Relationship(back_populates="items")
    service: Service | None = Relationship()


class QuoteItemPublic(QuoteItemBase):
    id: uuid.UUID
    quote_id: uuid.UUID
    service_id: uuid.UUID | None = None


# ============================================================================
# FIXPHONE ENTITY: INVOICE & INVOICE ITEM
# ============================================================================


class InvoiceBase(SQLModel):
    invoice_number: str = Field(unique=True, index=True, max_length=50)  # INV-2026-0001
    subtotal: float = Field(default=0.0)
    discount_amount: float = Field(default=0.0)
    tax_amount: float = Field(default=0.0)
    total_amount: float = Field(default=0.0)
    status: str = Field(
        default="UNPAID", max_length=50, index=True
    )  # UNPAID, PAID, PARTIALLY_PAID, CANCELLED
    issue_date: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    due_date: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    notes: str | None = Field(default=None, max_length=1000)


class InvoiceCreate(InvoiceBase):
    appointment_id: uuid.UUID
    customer_id: uuid.UUID


class InvoiceUpdate(SQLModel):
    subtotal: float | None = None
    discount_amount: float | None = None
    tax_amount: float | None = None
    total_amount: float | None = None
    status: str | None = Field(default=None, max_length=50)
    due_date: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)


class Invoice(InvoiceBase, table=True):
    __tablename__ = "invoice"
    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="check_invoice_subtotal_non_negative"),
        CheckConstraint(
            "discount_amount >= 0", name="check_invoice_discount_non_negative"
        ),
        CheckConstraint("tax_amount >= 0", name="check_invoice_tax_non_negative"),
        CheckConstraint(
            "total_amount >= 0", name="check_invoice_total_amount_non_negative"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # One-to-one unique relationship with appointment; RESTRICT ondelete prevents losing accounting audit
    appointment_id: uuid.UUID = Field(
        foreign_key="appointment.id",
        ondelete="RESTRICT",
        unique=True,
        nullable=False,
        index=True,
    )
    customer_id: uuid.UUID = Field(
        foreign_key="customer.id", ondelete="RESTRICT", nullable=False, index=True
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    appointment: Appointment = Relationship(back_populates="invoice")
    customer: Customer = Relationship(back_populates="invoices")
    items: list[InvoiceItem] = Relationship(
        back_populates="invoice", cascade_delete=True
    )
    payments: list[Payment] = Relationship(back_populates="invoice")


class InvoicePublic(InvoiceBase):
    id: uuid.UUID
    appointment_id: uuid.UUID
    customer_id: uuid.UUID
    created_at: datetime | None = None


class InvoiceItemBase(SQLModel):
    item_name: str = Field(max_length=255)
    unit_price: float = Field(default=0.0)
    quantity: int = Field(default=1)
    total_price: float = Field(default=0.0)


class InvoiceItemCreate(InvoiceItemBase):
    invoice_id: uuid.UUID


class InvoiceItem(InvoiceItemBase, table=True):
    __tablename__ = "invoice_item"
    __table_args__ = (
        CheckConstraint(
            "unit_price >= 0", name="check_invoice_item_unit_price_non_negative"
        ),
        CheckConstraint("quantity > 0", name="check_invoice_item_quantity_positive"),
        CheckConstraint(
            "total_price >= 0", name="check_invoice_item_total_price_non_negative"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    invoice_id: uuid.UUID = Field(
        foreign_key="invoice.id", ondelete="CASCADE", nullable=False, index=True
    )

    invoice: Invoice = Relationship(back_populates="items")


class InvoiceItemPublic(InvoiceItemBase):
    id: uuid.UUID
    invoice_id: uuid.UUID


# ============================================================================
# FIXPHONE ENTITY: PAYMENT
# ============================================================================


class PaymentBase(SQLModel):
    payment_number: str = Field(unique=True, index=True, max_length=50)  # PAY-2026-0001
    amount: float = Field(nullable=False)
    payment_method: str = Field(
        max_length=50
    )  # CASH, BANK_TRANSFER, CREDIT_CARD, MOMO, VNPAY
    payment_status: str = Field(
        default="SUCCESS", max_length=50, index=True
    )  # SUCCESS, PENDING, FAILED, REFUNDED
    transaction_reference: str | None = Field(default=None, max_length=100)
    paid_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    notes: str | None = Field(default=None, max_length=500)


class PaymentCreate(PaymentBase):
    invoice_id: uuid.UUID


class Payment(PaymentBase, table=True):
    __tablename__ = "payment"
    __table_args__ = (
        CheckConstraint("amount > 0", name="check_payment_amount_positive"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    invoice_id: uuid.UUID = Field(
        foreign_key="invoice.id", ondelete="RESTRICT", nullable=False, index=True
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    invoice: Invoice = Relationship(back_populates="payments")


class PaymentPublic(PaymentBase):
    id: uuid.UUID
    invoice_id: uuid.UUID
    created_at: datetime | None = None


# ============================================================================
# FIXPHONE ENTITY: REVIEW
# ============================================================================


class ReviewBase(SQLModel):
    rating: int = Field(nullable=False)  # 1 to 5
    comment: str | None = Field(default=None, max_length=1000)


class ReviewCreate(ReviewBase):
    appointment_id: uuid.UUID
    customer_id: uuid.UUID
    technician_id: uuid.UUID | None = None


class Review(ReviewBase, table=True):
    __tablename__ = "review"
    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5", name="check_review_rating_1_to_5"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Unique constraint: exactly one review per appointment
    appointment_id: uuid.UUID = Field(
        foreign_key="appointment.id",
        ondelete="RESTRICT",
        unique=True,
        nullable=False,
        index=True,
    )
    customer_id: uuid.UUID = Field(
        foreign_key="customer.id", ondelete="RESTRICT", nullable=False, index=True
    )
    technician_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="technician.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    appointment: Appointment = Relationship(back_populates="review")
    customer: Customer = Relationship(back_populates="reviews")
    technician: Technician | None = Relationship(back_populates="reviews")


class ReviewPublic(ReviewBase):
    id: uuid.UUID
    appointment_id: uuid.UUID
    customer_id: uuid.UUID
    technician_id: uuid.UUID | None = None
    created_at: datetime | None = None


# ============================================================================
# FIXPHONE ENTITY: NOTIFICATION
# ============================================================================


class NotificationBase(SQLModel):
    title: str = Field(max_length=255)
    message: str = Field(max_length=1000)
    notification_type: str = Field(
        default="STATUS_UPDATE", max_length=50
    )  # APPOINTMENT_REMINDER, STATUS_UPDATE, PAYMENT_CONFIRMATION, PROMOTION
    is_read: bool = Field(default=False, index=True)


class NotificationCreate(NotificationBase):
    customer_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class Notification(NotificationBase, table=True):
    __tablename__ = "notification"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Index on customer_id & is_read: Fast unread notification badge loading
    customer_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="customer.id",
        ondelete="CASCADE",
        nullable=True,
        index=True,
    )
    user_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        ondelete="CASCADE",
        nullable=True,
        index=True,
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )

    customer: Customer | None = Relationship(back_populates="notifications")
    user: User | None = Relationship()


class NotificationPublic(NotificationBase):
    id: uuid.UUID
    customer_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    created_at: datetime | None = None


# ============================================================================
# FIXPHONE ENTITY: SYSTEM LOG / ACTIVITY LOG
# ============================================================================


class SystemLogBase(SQLModel):
    action: str = Field(max_length=100, index=True)
    entity_name: str = Field(max_length=100)
    entity_id: str = Field(max_length=100)
    details: str | None = Field(default=None, max_length=2000)
    ip_address: str | None = Field(default=None, max_length=50)


class SystemLogCreate(SystemLogBase):
    user_id: uuid.UUID | None = None


class SystemLog(SystemLogBase, table=True):
    __tablename__ = "system_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )

    user: User | None = Relationship()


class SystemLogPublic(SystemLogBase):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    created_at: datetime | None = None


# ============================================================================
# GENERIC & AUTH PAYLOAD SCHEMAS
# ============================================================================


class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
