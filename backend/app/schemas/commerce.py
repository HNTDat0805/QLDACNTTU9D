import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models import (
    InvoiceItemPublic,
    InvoicePublic,
    NotificationPublic,
    PaymentPublic,
    ReviewPublic,
)


class InvoiceIssue(BaseModel):
    quote_id: uuid.UUID


class PaymentRecord(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    payment_method: Literal["CASH", "BANK_TRANSFER"]
    request_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=500)


class InvoiceDetail(InvoicePublic):
    items: list[InvoiceItemPublic]
    payments: list[PaymentPublic]
    paid_amount: float
    balance: float


class InvoicesPage(BaseModel):
    data: list[InvoiceDetail]
    count: int


class ReviewSubmit(BaseModel):
    appointment_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewsPage(BaseModel):
    data: list[ReviewPublic]
    count: int


class NotificationsPage(BaseModel):
    data: list[NotificationPublic]
    count: int
    unread_count: int


class MonthRevenue(BaseModel):
    month: str
    amount: float


class StatisticsResponse(BaseModel):
    start_date: date
    end_date: date
    receipts_total: float
    outstanding_total: float
    appointment_count: int
    completed_count: int
    customer_count: int
    monthly_revenue: list[MonthRevenue]


class ServiceInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    base_price: float = Field(ge=0, allow_inf_nan=False)
    estimated_duration_minutes: int = Field(gt=0, le=1440)
    is_active: bool = True
