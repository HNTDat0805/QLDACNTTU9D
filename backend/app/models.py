import uuid
from datetime import UTC, date, datetime, time
from enum import StrEnum
from typing import Optional, Self

from pydantic import EmailStr, field_validator, model_validator
from sqlalchemy import CheckConstraint, Date, DateTime, Time
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# ============================================================================
# USER & AUTHENTICATION MODELS (Template Core + Extended Role)
# ============================================================================


class UserRole(StrEnum):
    CUSTOMER = "customer"
    STAFF = "staff"
    TECHNICIAN = "technician"
    MANAGER = "manager"
    ADMIN = "admin"


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    role: str = Field(default=UserRole.CUSTOMER.value, max_length=50, index=True)

    @field_validator("role")
    @classmethod
    def validate_user_role(cls, value: str) -> str:
        return UserRole(value).value


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

    @field_validator("role")
    @classmethod
    def validate_user_role(cls, value: str | None) -> str | None:
        return UserRole(value).value if value is not None else None


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Password cannot be blank or only whitespace")
        return v


class User(UserBase, table=True):
    __tablename__ = "user"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)  # noqa: UP037
    customer_profile: Optional["Customer"] = Relationship(back_populates="user")  # noqa: UP037, UP045
    technician_profile: Optional["Technician"] = Relationship(back_populates="user")  # noqa: UP037, UP045
    refresh_tokens: list["RefreshToken"] = Relationship(  # noqa: UP037
        back_populates="user", cascade_delete=True
    )
    password_reset_tokens: list["PasswordResetToken"] = Relationship(  # noqa: UP037
        back_populates="user", cascade_delete=True
    )


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
        sa_type=DateTime(timezone=True),
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
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
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
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
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
    code: str | None = Field(
        default=None,
        unique=True,
        index=True,
        max_length=50,
        description="Mã định danh dịch vụ duy nhất (ví dụ: SVC-SCREEN-01)",
    )
    name: str = Field(
        unique=True,
        index=True,
        max_length=255,
        description="Tên dịch vụ sửa chữa",
    )
    description: str | None = Field(
        default=None, max_length=1000, description="Mô tả chi tiết dịch vụ"
    )
    base_price: float = Field(
        default=0.0, ge=0.0, description="Giá dịch vụ khởi điểm (VNĐ, >= 0)"
    )
    estimated_duration_minutes: int = Field(
        default=30,
        gt=0,
        description="Thời gian sửa chữa ước tính (phút, > 0)",
    )
    is_active: bool = Field(
        default=True,
        index=True,
        description="Trạng thái dịch vụ đang kinh doanh (ẩn/hiện)",
    )


class ServiceCreate(SQLModel):
    code: str | None = Field(
        default=None,
        max_length=50,
        description="Mã dịch vụ duy nhất (nếu không cung cấp, hệ thống tự động sinh)",
    )
    name: str = Field(
        min_length=1,
        max_length=255,
        description="Tên dịch vụ sửa chữa (bắt buộc, không để trống)",
    )
    description: str | None = Field(default=None, max_length=1000)
    base_price: float = Field(
        default=0.0,
        ge=0.0,
        description="Giá dịch vụ khởi điểm (phải >= 0)",
    )
    estimated_duration_minutes: int = Field(
        default=30,
        gt=0,
        description="Thời gian sửa chữa dự kiến (phút, phải > 0)",
    )
    is_active: bool = Field(default=True)

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError(
                "Tên dịch vụ không được để trống hoặc chỉ chứa khoảng trắng"
            )
        return cleaned

    @field_validator("code")
    @classmethod
    def validate_code_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            raise ValueError(
                "Mã dịch vụ không được để trống hoặc chỉ chứa khoảng trắng"
            )
        return cleaned.upper()


class ServiceUpdate(SQLModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Tên dịch vụ mới",
    )
    description: str | None = Field(default=None, max_length=1000)
    base_price: float | None = Field(
        default=None, ge=0.0, description="Giá dịch vụ mới (>= 0)"
    )
    estimated_duration_minutes: int | None = Field(
        default=None,
        gt=0,
        description="Thời gian sửa chữa dự kiến mới (phút, > 0)",
    )
    is_active: bool | None = Field(
        default=None, description="Trạng thái hiển thị dịch vụ"
    )
    code: str | None = Field(
        default=None,
        max_length=50,
        description="Mã định danh không được phép sửa đổi",
    )

    @field_validator("name")
    @classmethod
    def validate_update_name(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError(
                    "Tên dịch vụ không được để trống hoặc chỉ chứa khoảng trắng"
                )
            return cleaned
        return v


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
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )

    appointment_services: list[AppointmentService] = Relationship(
        back_populates="service"
    )


class ServicePublic(ServiceBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ServicesPublic(SQLModel):
    data: list[ServicePublic]
    count: int


class ServiceResponse(SQLModel):
    success: bool = True
    message: str
    data: ServicePublic


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
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
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
        sa_type=DateTime(timezone=True),
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
    appointment_date: datetime = Field(sa_type=DateTime(timezone=True), index=True)
    # Index on status: Filter appointments by PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    status: str = Field(default="PENDING", max_length=50, index=True)
    cancellation_reason: str | None = Field(default=None, max_length=500)
    customer_notes: str | None = Field(default=None, max_length=1000)
    technician_diagnosis: str | None = Field(default=None, max_length=1000)
    estimated_completion_date: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    actual_completion_date: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
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
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
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
    quotes: list["Quote"] = Relationship(back_populates="appointment")  # noqa: UP037
    invoice: Optional["Invoice"] = Relationship(back_populates="appointment")  # noqa: UP037, UP045
    review: Optional["Review"] = Relationship(back_populates="appointment")  # noqa: UP037, UP045


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
        sa_type=DateTime(timezone=True),
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
        sa_type=DateTime(timezone=True),
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
    valid_until: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
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
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
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
        sa_type=DateTime(timezone=True),
    )
    due_date: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
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
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
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
        sa_type=DateTime(timezone=True),
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
        sa_type=DateTime(timezone=True),
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
    rating: int = Field(
        nullable=False, ge=1, le=5, description="Điểm đánh giá từ 1 đến 5 sao"
    )
    comment: str | None = Field(
        default=None, max_length=1000, description="Nội dung nhận xét"
    )


class ReviewCreate(ReviewBase):
    appointment_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    technician_id: uuid.UUID | None = None


class ReviewCreateRequest(SQLModel):
    appointment_id: uuid.UUID
    rating: int = Field(ge=1, le=5, description="Điểm đánh giá từ 1 đến 5 sao")
    comment: str | None = Field(
        default=None, max_length=1000, description="Nội dung nhận xét"
    )
    customer_id: uuid.UUID | None = Field(
        default=None,
        description="ID khách hàng (tùy chọn, tự động xác định từ lịch hẹn)",
    )


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
        sa_type=DateTime(timezone=True),
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
    customer_name: str | None = None
    technician_name: str | None = None
    appointment_number: str | None = None


class ReviewsPublic(SQLModel):
    data: list[ReviewPublic]
    count: int
    average_rating: float | None = None


class ReviewResponse(SQLModel):
    success: bool = True
    message: str
    data: ReviewPublic


# ============================================================================
# FIXPHONE ENTITY: NOTIFICATION
# ============================================================================


class NotificationBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=1000)
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
        sa_type=DateTime(timezone=True),
        index=True,
    )

    customer: Customer | None = Relationship(back_populates="notifications")
    user: User | None = Relationship()


class NotificationPublic(NotificationBase):
    id: uuid.UUID
    customer_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    created_at: datetime | None = None


class NotificationsPublic(SQLModel):
    data: list[NotificationPublic]
    count: int
    unread_count: int


class UnreadNotificationCount(SQLModel):
    unread_count: int


class MarkAllReadResponse(SQLModel):
    message: str = "Đã đánh dấu tất cả thông báo là đã đọc"
    updated_count: int


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
        sa_type=DateTime(timezone=True),
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
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshTokenInput(SQLModel):
    refresh_token: str


class TokenPayload(SQLModel):
    sub: str | None = None
    type: str | None = None
    role: str | None = None
    email: str | None = None
    jti: str | None = None


# ============================================================================
# FIXPHONE ENTITY: REFRESH TOKEN (SERVER-SIDE TRACKING & REVOCATION)
# ============================================================================


class RefreshTokenBase(SQLModel):
    user_id: uuid.UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    token_hash: str = Field(unique=True, index=True, max_length=64)
    jti: str = Field(unique=True, index=True, max_length=64)
    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        index=True,
    )
    is_revoked: bool = Field(default=False, index=True)
    revoked_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    replaced_by_jti: str | None = Field(default=None, max_length=64)


class RefreshToken(RefreshTokenBase, table=True):
    __tablename__ = "refresh_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )

    user: User = Relationship(back_populates="refresh_tokens")


# ============================================================================
# FIXPHONE ENTITY: PASSWORD RESET TOKEN (DATABASE-BACKED & SINGLE-USE)
# ============================================================================


class PasswordResetTokenBase(SQLModel):
    user_id: uuid.UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    token_hash: str = Field(unique=True, index=True, max_length=64)
    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        index=True,
    )
    is_used: bool = Field(default=False, index=True)
    used_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )


class PasswordResetToken(PasswordResetTokenBase, table=True):
    __tablename__ = "password_reset_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )

    user: User = Relationship(back_populates="password_reset_tokens")


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# ============================================================================
# SLOT & APPOINTMENT BOOKING API SCHEMAS
# ============================================================================


class AvailableSlotItem(SQLModel):
    start_time: str
    end_time: str
    available: bool = True
    technician_id: uuid.UUID | None = None


class AvailableSlotsResponse(SQLModel):
    date: date
    service_id: uuid.UUID
    available_slots: list[AvailableSlotItem]


class SlotCheckRequest(SQLModel):
    service_id: uuid.UUID
    appointment_date: date
    start_time: time
    technician_id: uuid.UUID | None = None
    exclude_appointment_id: uuid.UUID | None = None


class SlotCheckResponse(SQLModel):
    available: bool
    reason: str | None = None
    message: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    technician_id: uuid.UUID | None = None


class AppointmentBookingCreate(SQLModel):
    customer_id: uuid.UUID | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: EmailStr | None = None
    customer_address: str | None = None
    service_id: uuid.UUID | None = None
    service_ids: list[uuid.UUID] | None = None
    device_id: uuid.UUID | None = None
    device_type: str | None = None
    device_brand: str | None = None
    device_model: str | None = None
    appointment_date: date
    start_time: time
    technician_id: uuid.UUID | None = None
    description: str | None = None

    @model_validator(mode="after")
    def validate_customer_and_service(self) -> Self:
        if not self.customer_id and not (
            self.customer_phone and self.customer_phone.strip()
        ):
            raise ValueError("Cần cung cấp customer_id hoặc customer_phone")
        if self.customer_phone is not None:
            cleaned_phone = self.customer_phone.strip()
            if len(cleaned_phone) < 8 or len(cleaned_phone) > 20:
                raise ValueError("Số điện thoại phải từ 8 đến 20 ký tự")
            self.customer_phone = cleaned_phone
        if not self.service_id and not self.service_ids:
            raise ValueError(
                "Cần chọn ít nhất một dịch vụ sửa chữa (service_id hoặc service_ids)"
            )
        return self


class AppointmentBookingUpdate(SQLModel):
    appointment_date: date | None = None
    start_time: time | None = None
    technician_id: uuid.UUID | None = None
    description: str | None = None
    reschedule_reason: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    device_brand: str | None = None
    device_model: str | None = None

    @field_validator("contact_phone")
    @classmethod
    def validate_contact_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            return None
        if len(cleaned) < 8 or len(cleaned) > 20:
            raise ValueError("Số điện thoại liên hệ phải từ 8 đến 20 ký tự")
        return cleaned


class AppointmentBookingResponse(SQLModel):
    appointment_id: uuid.UUID
    appointment_code: str
    appointment_date: date
    start_time: str
    status: str
    message: str
    end_time: str | None = None
    customer_id: uuid.UUID | None = None
    device_id: uuid.UUID | None = None
    technician_id: uuid.UUID | None = None
    total_amount: float | None = None
    service_names: list[str] | None = None


# ============================================================================
# APPOINTMENT CONFIRM & CANCEL API SCHEMAS
# ============================================================================


class AppointmentStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AppointmentConfirmData(SQLModel):
    id: uuid.UUID
    appointment_number: str
    status: str
    appointment_date: datetime
    customer_id: uuid.UUID
    technician_id: uuid.UUID | None = None


class AppointmentConfirmResponse(SQLModel):
    success: bool = True
    message: str
    data: AppointmentConfirmData


class AppointmentCancelRequest(SQLModel):
    reason: str = Field(min_length=1, max_length=500, description="Lý do hủy lịch hẹn")
    note: str | None = Field(
        default=None, max_length=1000, description="Ghi chú thêm khi hủy"
    )

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Lý do hủy không được để trống")
        return v.strip()


class AppointmentCancelData(SQLModel):
    id: uuid.UUID
    appointment_number: str
    status: str
    cancellation_reason: str | None = None
    customer_notes: str | None = None


class AppointmentCancelResponse(SQLModel):
    success: bool = True
    message: str
    data: AppointmentCancelData


# ============================================================================
# FIXPHONE MANAGEMENT & QUEUE & HISTORY API SCHEMAS
# ============================================================================


class CustomersPublic(SQLModel):
    data: list[CustomerPublic]
    count: int


class TechniciansPublic(SQLModel):
    data: list[TechnicianPublic]
    count: int


class TechnicianStatusUpdate(SQLModel):
    is_active: bool


class TechnicianSchedulesPublic(SQLModel):
    data: list[TechnicianSchedulePublic]
    count: int


class TechnicianScheduleStatusUpdate(SQLModel):
    status: str = Field(max_length=50)
    notes: str | None = Field(default=None, max_length=500)


class QueueItemPublic(SQLModel):
    appointment_id: uuid.UUID
    appointment_number: str
    status: str
    appointment_date: datetime
    customer_id: uuid.UUID
    customer_name: str
    customer_phone: str
    device_id: uuid.UUID
    device_info: str
    technician_id: uuid.UUID | None = None
    technician_name: str | None = None
    service_names: list[str] = Field(default_factory=list)
    total_amount: float = 0.0
    estimated_duration_minutes: int = 30
    queue_position: int = 1
    technician_diagnosis: str | None = None
    customer_notes: str | None = None
    created_at: datetime | None = None


class QueueListResponse(SQLModel):
    data: list[QueueItemPublic]
    count: int
    date: date | None = None


class QueueStatusUpdate(SQLModel):
    status: str = Field(
        max_length=50,
        description="Trạng thái mới: CONFIRMED, IN_PROGRESS, COMPLETED, CANCELLED",
    )
    technician_id: uuid.UUID | None = None
    technician_diagnosis: str | None = Field(default=None, max_length=1000)
    note: str | None = Field(default=None, max_length=1000)


class AppointmentServiceItemDetail(SQLModel):
    service_id: uuid.UUID
    service_name: str
    price_at_booking: float
    quantity: int = 1
    notes: str | None = None


class AppointmentHistoryDetail(SQLModel):
    id: uuid.UUID
    appointment_number: str
    appointment_date: datetime
    status: str
    cancellation_reason: str | None = None
    customer_notes: str | None = None
    technician_diagnosis: str | None = None
    estimated_completion_date: datetime | None = None
    actual_completion_date: datetime | None = None
    total_amount: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    customer: CustomerPublic | None = None
    device: DevicePublic | None = None
    technician: TechnicianPublic | None = None
    services: list[AppointmentServiceItemDetail] = Field(default_factory=list)
    status_history: list[RepairStatusHistoryPublic] = Field(default_factory=list)


class AppointmentsHistoryPublic(SQLModel):
    data: list[AppointmentHistoryDetail]
    count: int


# ============================================================================
# FIXPHONE REPAIR ORDER / DEVICE INTAKE SCHEMAS
# ============================================================================


class DeviceIntakeCreate(SQLModel):
    appointment_id: uuid.UUID | None = Field(
        default=None, description="ID lịch hẹn có sẵn nếu khách đã đặt lịch hẹn trước"
    )

    customer_id: uuid.UUID | None = Field(
        default=None, description="ID khách hàng nếu đã có trong hệ thống"
    )
    customer_name: str | None = Field(
        default=None,
        max_length=255,
        description="Họ và tên khách hàng (bắt buộc nếu không có customer_id và appointment_id)",
    )
    customer_phone: str | None = Field(
        default=None,
        max_length=20,
        description="Số điện thoại khách hàng (bắt buộc nếu không có customer_id và appointment_id)",
    )
    customer_email: str | None = Field(default=None, max_length=255)
    customer_address: str | None = Field(default=None, max_length=500)

    device_id: uuid.UUID | None = Field(
        default=None, description="ID thiết bị nếu đã có trong hệ thống"
    )
    brand: str | None = Field(
        default=None,
        max_length=100,
        description="Hãng sản xuất thiết bị (Apple, Samsung, Xiaomi...)",
    )
    model: str | None = Field(
        default=None,
        max_length=100,
        description="Dòng máy (iPhone 13, Galaxy S23...)",
    )
    device_type: str = Field(default="Smartphone", max_length=50)
    serial_number: str | None = Field(default=None, max_length=100)
    imei: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=50)

    physical_condition: str = Field(
        min_length=1,
        max_length=1000,
        description="Tình trạng ngoại quan máy khi tiếp nhận (vỡ màn hình, cấn móp, trầy xước...)",
    )
    fault_description: str = Field(
        min_length=1,
        max_length=1000,
        description="Mô tả lỗi hoặc triệu chứng hỏng hóc từ khách hàng",
    )
    accessories_received: str | None = Field(
        default=None,
        max_length=500,
        description="Phụ kiện khách bàn giao (sạc, cáp, que SIM, ốp lưng, hộp...)",
    )

    technician_id: uuid.UUID | None = Field(
        default=None, description="Kỹ thuật viên phụ trách tiếp nhận/sửa chữa (nếu có)"
    )
    service_ids: list[uuid.UUID] | None = Field(
        default=None, description="Danh sách ID dịch vụ sửa chữa dự kiến"
    )
    estimated_completion_date: datetime | None = Field(
        default=None, description="Thời gian dự kiến hoàn thành"
    )
    initial_status: AppointmentStatus = Field(
        default=AppointmentStatus.CONFIRMED,
        description="Trạng thái ban đầu của phiếu: CONFIRMED hoặc IN_PROGRESS",
    )

    @field_validator("physical_condition")
    @classmethod
    def validate_physical_condition(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Tình trạng ngoại quan thiết bị không được để trống")
        return v.strip()

    @field_validator("customer_phone")
    @classmethod
    def validate_intake_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            return None
        if len(cleaned) < 8 or len(cleaned) > 20:
            raise ValueError("Số điện thoại khách hàng phải từ 8 đến 20 ký tự")
        return cleaned

    @field_validator("fault_description")
    @classmethod
    def validate_fault_description(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Mô tả lỗi thiết bị không được để trống")
        return v.strip()

    @field_validator("initial_status")
    @classmethod
    def validate_initial_status(cls, v: AppointmentStatus) -> AppointmentStatus:
        if v not in (AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS):
            raise ValueError(
                "Trạng thái ban đầu của phiếu tiếp nhận chỉ có thể là CONFIRMED hoặc IN_PROGRESS"
            )
        return v

    @model_validator(mode="after")
    def validate_intake_payload(self) -> Self:
        # Nếu không có appointment_id (tiếp nhận walk-in trực tiếp)
        if not self.appointment_id:
            # Phải có customer_id hoặc (customer_name và customer_phone)
            if not self.customer_id:
                if not self.customer_name or not self.customer_name.strip():
                    raise ValueError(
                        "Cần cung cấp tên khách hàng (customer_name) hoặc customer_id"
                    )
                if not self.customer_phone or not self.customer_phone.strip():
                    raise ValueError(
                        "Cần cung cấp số điện thoại khách hàng (customer_phone) hoặc customer_id"
                    )
            # Phải có device_id hoặc (brand và model)
            if not self.device_id:
                if not self.brand or not self.brand.strip():
                    raise ValueError(
                        "Cần cung cấp hãng thiết bị (brand) hoặc device_id"
                    )
                if not self.model or not self.model.strip():
                    raise ValueError(
                        "Cần cung cấp dòng máy thiết bị (model) hoặc device_id"
                    )
        return self


class DeviceIntakeDetail(SQLModel):
    id: uuid.UUID
    appointment_number: str
    status: str
    appointment_date: datetime
    customer_id: uuid.UUID
    customer_name: str
    customer_phone: str
    device_id: uuid.UUID
    device_brand: str
    device_model: str
    device_imei: str | None = None
    device_color: str | None = None
    physical_condition: str
    fault_description: str
    accessories_received: str | None = None
    technician_id: uuid.UUID | None = None
    technician_name: str | None = None
    estimated_completion_date: datetime | None = None
    total_amount: float = 0.0
    services: list[AppointmentServiceItemDetail] = Field(default_factory=list)
    created_at: datetime | None = None


class DeviceIntakeResponse(SQLModel):
    success: bool = True
    message: str
    data: DeviceIntakeDetail


# ============================================================================
# FIXPHONE REPAIR QUOTATION SCHEMAS
# ============================================================================


class QuoteStatus(StrEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class QuotationItemCreate(SQLModel):
    service_id: uuid.UUID | None = Field(
        default=None, description="ID dịch vụ từ danh mục (nếu có)"
    )
    item_name: str | None = Field(
        default=None,
        max_length=255,
        description="Tên hạng mục sửa chữa hoặc linh kiện (nếu không có service_id thì bắt buộc)",
    )
    unit_price: float | None = Field(
        default=None,
        ge=0,
        description="Đơn giá hạng mục (nếu không truyền sẽ lấy theo giá gốc dịch vụ)",
    )
    quantity: int = Field(
        default=1,
        gt=0,
        description="Số lượng (phải lớn hơn 0)",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Ghi chú chi tiết cho hạng mục này",
    )

    @field_validator("item_name")
    @classmethod
    def validate_item_name(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Tên hạng mục không được là khoảng trắng")
        return v.strip() if v else None


class QuotationCreate(SQLModel):
    appointment_id: uuid.UUID | None = Field(
        default=None, description="UUID của phiếu sửa chữa"
    )
    appointment_number: str | None = Field(
        default=None,
        max_length=50,
        description="Mã phiếu sửa chữa (ví dụ: APPT-20261024-XXXX)",
    )
    items: list[QuotationItemCreate] = Field(
        min_length=1,
        description="Danh sách các hạng mục báo giá (ít nhất 1 hạng mục)",
    )
    valid_until: datetime | None = Field(
        default=None,
        description="Thời hạn hiệu lực của báo giá (nếu có)",
    )
    customer_notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Ghi chú gửi cho khách hàng",
    )
    status: QuoteStatus = Field(
        default=QuoteStatus.DRAFT,
        description="Trạng thái ban đầu của báo giá (mặc định DRAFT)",
    )

    @model_validator(mode="after")
    def validate_appointment_reference(self) -> Self:
        if not self.appointment_id and (
            not self.appointment_number or not self.appointment_number.strip()
        ):
            raise ValueError(
                "Cần cung cấp ít nhất một định danh: appointment_id hoặc appointment_number"
            )
        return self


class QuotationItemDetail(SQLModel):
    id: uuid.UUID
    service_id: uuid.UUID | None = None
    item_name: str
    unit_price: float
    quantity: int
    total_price: float
    notes: str | None = None


class QuotationDetail(SQLModel):
    id: uuid.UUID
    quote_number: str
    appointment_id: uuid.UUID
    appointment_number: str
    customer_id: uuid.UUID
    customer_name: str
    customer_phone: str
    device_info: str
    total_amount: float
    status: str
    valid_until: datetime | None = None
    customer_notes: str | None = None
    items: list[QuotationItemDetail] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class QuotationResponse(SQLModel):
    success: bool = True
    message: str
    data: QuotationDetail


class QuotationAcceptRequest(SQLModel):
    note: str | None = Field(
        default=None,
        max_length=1000,
        description="Ghi chú thêm khi duyệt báo giá sửa chữa (tùy chọn)",
    )


class QuotationsPublic(SQLModel):
    data: list[QuotationDetail]
    count: int


# ============================================================================
# FIXPHONE DEVICE & REPAIR ORDER MANAGEMENT SCHEMAS
# ============================================================================


class DeviceResponse(SQLModel):
    success: bool = True
    message: str
    data: DevicePublic


class RepairStatusUpdateRequest(SQLModel):
    status: AppointmentStatus = Field(
        description="Trạng thái sửa chữa mới (PENDING, CONFIRMED, IN_PROGRESS, COMPLETED, CANCELLED)"
    )
    note: str | None = Field(
        default=None,
        max_length=1000,
        description="Ghi chú chi tiết về việc chuyển trạng thái sửa chữa",
    )
    technician_diagnosis: str | None = Field(
        default=None,
        max_length=1000,
        description="Chẩn đoán kỹ thuật bổ sung (tùy chọn)",
    )
    cancellation_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Lý do hủy (nếu chuyển sang trạng thái CANCELLED)",
    )


class RepairStatusUpdateData(SQLModel):
    id: uuid.UUID
    appointment_number: str
    previous_status: str
    current_status: str
    note: str | None = None
    technician_diagnosis: str | None = None
    actual_completion_date: datetime | None = None
    updated_at: datetime | None = None
    history_id: uuid.UUID | None = None


class RepairStatusUpdateResponse(SQLModel):
    success: bool = True
    message: str
    data: RepairStatusUpdateData


class AssignTechnicianRequest(SQLModel):
    technician_id: uuid.UUID = Field(description="ID của kỹ thuật viên được phân công")
    note: str | None = Field(
        default=None,
        max_length=500,
        description="Ghi chú phân công công việc (tùy chọn)",
    )


class AssignTechnicianData(SQLModel):
    id: uuid.UUID
    appointment_number: str
    technician_id: uuid.UUID
    technician_name: str
    technician_phone: str
    specialization: str | None = None
    status: str
    assigned_at: datetime | None = None


class AssignTechnicianResponse(SQLModel):
    success: bool = True
    message: str
    data: AssignTechnicianData


# ============================================================================
# FIXPHONE APPOINTMENT TECHNICIAN ASSIGNMENT SCHEMAS
# ============================================================================


class AppointmentAssignTechnicianRequest(SQLModel):
    technician_id: uuid.UUID = Field(
        description="Mã UUID của kỹ thuật viên cần phân công"
    )
    note: str | None = Field(
        default=None,
        max_length=500,
        description="Ghi chú phân công công việc (tùy chọn)",
    )


class AppointmentAssignTechnicianData(SQLModel):
    appointment_id: uuid.UUID
    appointment_number: str
    appointment_date: datetime
    technician_id: uuid.UUID
    technician_name: str
    technician_phone: str | None = None
    technician_specialization: str | None = None
    status: str
    assigned_at: datetime
    note: str | None = None


class AppointmentAssignTechnicianResponse(SQLModel):
    success: bool = True
    message: str
    data: AppointmentAssignTechnicianData


# ============================================================================
# TASK 315 & 319: INVOICE & PAYMENT API SCHEMAS
# ============================================================================


class InvoiceStatus(StrEnum):
    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    CASH = "cash"
    COD = "cod"
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    E_WALLET = "e_wallet"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class InvoiceCreateRequest(SQLModel):
    repair_order_id: uuid.UUID | str | int = Field(
        description="ID hoặc mã đơn sửa chữa (UUID, mã số hoặc chuỗi định danh)"
    )
    notes: str | None = Field(
        default=None, max_length=1000, description="Ghi chú hóa đơn"
    )


class InvoiceItemDetail(SQLModel):
    id: uuid.UUID
    item_name: str
    quantity: int
    unit_price: float
    total_price: float


class InvoiceDetail(SQLModel):
    id: uuid.UUID
    invoice_code: str
    invoice_number: str
    repair_order_id: uuid.UUID
    appointment_number: str
    customer_id: uuid.UUID
    customer_name: str
    customer_phone: str | None = None
    subtotal: float
    discount_amount: float = 0.0
    tax_amount: float = 0.0
    total_amount: float
    paid_amount: float = 0.0
    remaining_amount: float = 0.0
    status: str
    items: list[InvoiceItemDetail] = Field(default_factory=list)
    created_at: datetime | None = None
    notes: str | None = None


class InvoiceResponse(SQLModel):
    success: bool = True
    message: str
    data: InvoiceDetail


class InvoicesPublic(SQLModel):
    data: list[InvoiceDetail]
    count: int


class PaymentCreateRequest(SQLModel):
    invoice_id: uuid.UUID | str | int = Field(
        description="ID hoặc mã số của hóa đơn cần thanh toán"
    )
    amount: float = Field(
        gt=0,
        description="Số tiền thanh toán (phải lớn hơn 0)",
    )
    payment_method: str = Field(
        default="cash",
        description="Phương thức thanh toán: cash (tiền mặt), cod (khi nhận máy), bank_transfer (chuyển khoản/QR), card (thẻ ATM/Visa), e_wallet (ví điện tử)",
    )
    transaction_code: str | None = Field(
        default=None,
        max_length=100,
        description="Mã giao dịch / mã tham chiếu từ ngân hàng hoặc cổng thanh toán (nếu có)",
    )
    note: str | None = Field(
        default=None,
        max_length=500,
        description="Ghi chú giao dịch thanh toán",
    )


class PaymentDetail(SQLModel):
    id: uuid.UUID
    payment_code: str
    payment_number: str
    invoice_id: uuid.UUID
    invoice_code: str
    amount: float
    payment_method: str
    status: str
    paid_at: datetime
    transaction_code: str | None = None
    transaction_reference: str | None = None
    recorded_by: str | None = None
    recorded_by_user_id: uuid.UUID | None = None
    note: str | None = None
    created_at: datetime | None = None
    invoice_status_after_payment: str | None = None
    invoice_remaining_amount: float | None = None


class PaymentResponse(SQLModel):
    success: bool = True
    message: str
    data: PaymentDetail


class PaymentsPublic(SQLModel):
    data: list[PaymentDetail]
    count: int


# ============================================================================
# TASK 321 & 322: ACCOUNT MANAGEMENT & PASSWORD RESET SCHEMAS
# ============================================================================


class UserLockRequest(SQLModel):
    reason: str | None = Field(
        default=None, max_length=500, description="Lý do khóa tài khoản (tùy chọn)"
    )


class UserLockResponse(SQLModel):
    success: bool = True
    message: str
    data: UserPublic


class UserUnlockResponse(SQLModel):
    success: bool = True
    message: str
    data: UserPublic


class ForgotPasswordRequest(SQLModel):
    email: EmailStr = Field(
        description="Email đăng ký của tài khoản cần đặt lại mật khẩu"
    )


class ForgotPasswordResponse(SQLModel):
    success: bool = True
    message: str


class VerifyResetTokenRequest(SQLModel):
    token: str = Field(
        min_length=1, description="Mã token đặt lại mật khẩu cần xác thực"
    )


class VerifyResetTokenResponse(SQLModel):
    success: bool = True
    valid: bool = True
    email: str | None = None
    message: str


class ResetPasswordRequest(SQLModel):
    token: str = Field(min_length=1, description="Mã token đặt lại mật khẩu")
    new_password: str = Field(min_length=8, max_length=128, description="Mật khẩu mới")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Mật khẩu không được để trống hoặc chỉ có khoảng trắng")
        return v


class ResetPasswordResponse(SQLModel):
    success: bool = True
    message: str
