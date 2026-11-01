import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, func, or_, select

from app.api.deps import CurrentUser, RequireManager, RequireStaff, SessionDep
from app.models import (
    Appointment,
    Customer,
    Invoice,
    Message,
    Notification,
    NotificationPublic,
    RepairStatusHistory,
    Review,
    ReviewPublic,
)
from app.schemas.commerce import (
    InvoiceDetail,
    InvoiceIssue,
    InvoicesPage,
    NotificationsPage,
    PaymentRecord,
    ReviewsPage,
    ReviewSubmit,
    StatisticsResponse,
)
from app.services import commerce_service
from app.services.access_service import check_appointment_access

router = APIRouter(tags=["commerce"])


@router.get("/invoices", response_model=InvoicesPage)
def read_invoices(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> InvoicesPage:
    return commerce_service.read_invoices(session, current_user, skip, limit)


@router.post("/invoices", response_model=InvoiceDetail, status_code=201)
def issue_invoice(
    session: SessionDep, current_user: RequireStaff, body: InvoiceIssue
) -> InvoiceDetail:
    return commerce_service.issue_invoice(session, current_user, body.quote_id)


@router.get("/invoices/{invoice_id}", response_model=InvoiceDetail)
def read_invoice(
    session: SessionDep, current_user: CurrentUser, invoice_id: uuid.UUID
) -> InvoiceDetail:
    commerce_service.check_billing_role(current_user)
    invoice = session.get(Invoice, invoice_id)
    appointment = session.get(Appointment, invoice.appointment_id) if invoice else None
    if not invoice or not appointment:
        raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")
    check_appointment_access(session, current_user, appointment)
    return commerce_service.invoice_detail(session, invoice)


@router.post("/invoices/{invoice_id}/payments", response_model=InvoiceDetail)
def record_payment(
    session: SessionDep,
    current_user: RequireStaff,
    invoice_id: uuid.UUID,
    body: PaymentRecord,
) -> InvoiceDetail:
    return commerce_service.record_payment(session, current_user, invoice_id, body)


@router.post("/invoices/{invoice_id}/handover", response_model=Message)
def handover_device(
    session: SessionDep, current_user: RequireStaff, invoice_id: uuid.UUID
) -> Message:
    from app.services.access_service import is_reception

    if not is_reception(current_user):
        raise HTTPException(
            status_code=403, detail="Chỉ nhân viên tiếp nhận được bàn giao"
        )
    invoice = session.exec(
        select(Invoice).where(Invoice.id == invoice_id).with_for_update()
    ).first()
    if not invoice or invoice.status != "PAID":
        raise HTTPException(
            status_code=409,
            detail="Chỉ bàn giao thiết bị sau khi hóa đơn đã thanh toán đủ",
        )
    appointment = session.get(Appointment, invoice.appointment_id)
    if not appointment or appointment.status != "COMPLETED":
        raise HTTPException(status_code=409, detail="Phiếu sửa chữa chưa hoàn tất")
    existing = session.exec(
        select(RepairStatusHistory).where(
            RepairStatusHistory.appointment_id == appointment.id,
            col(RepairStatusHistory.note).like("[HANDOVER]%"),
        )
    ).first()
    if existing:
        return Message(message="Thiết bị đã được bàn giao")
    session.add(
        RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status=appointment.status,
            new_status=appointment.status,
            changed_by_user_id=current_user.id,
            note=f"[HANDOVER] Bàn giao thiết bị theo hóa đơn {invoice.invoice_number}",
        )
    )
    session.add(
        Notification(
            customer_id=appointment.customer_id,
            title="Đã bàn giao thiết bị",
            message=f"Thiết bị của phiếu {appointment.appointment_number} đã được bàn giao tại cửa hàng.",
        )
    )
    session.commit()
    return Message(message="Đã ghi nhận bàn giao thiết bị")


@router.get("/statistics", response_model=StatisticsResponse)
def read_statistics(
    session: SessionDep,
    _: RequireManager,
    start_date: date | None = None,
    end_date: date | None = None,
) -> StatisticsResponse:
    today = date.today()
    return commerce_service.statistics(
        session, start_date or today.replace(month=1, day=1), end_date or today
    )


@router.get("/reviews", response_model=ReviewsPage)
def read_my_reviews(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> ReviewsPage:
    query = select(Review).join(Customer).where(Customer.user_id == current_user.id)
    count = session.exec(
        select(func.count())
        .select_from(Review)
        .join(Customer)
        .where(Customer.user_id == current_user.id)
    ).one()
    return ReviewsPage(
        data=[
            ReviewPublic.model_validate(r)
            for r in session.exec(query.offset(skip).limit(limit)).all()
        ],
        count=count,
    )


@router.post("/reviews", response_model=ReviewPublic, status_code=201)
def submit_review(
    session: SessionDep, current_user: CurrentUser, body: ReviewSubmit
) -> ReviewPublic:
    appointment = session.exec(
        select(Appointment)
        .where(Appointment.id == body.appointment_id)
        .with_for_update()
    ).first()
    customer = session.get(Customer, appointment.customer_id) if appointment else None
    if not appointment or not customer or customer.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Chỉ khách hàng sở hữu lịch hẹn được đánh giá"
        )
    if appointment.status != "COMPLETED":
        raise HTTPException(
            status_code=409, detail="Chỉ đánh giá sau khi hoàn tất sửa chữa"
        )
    if session.exec(
        select(Review).where(Review.appointment_id == appointment.id)
    ).first():
        raise HTTPException(status_code=409, detail="Bạn đã đánh giá lịch hẹn này")
    review = Review(
        appointment_id=appointment.id,
        customer_id=appointment.customer_id,
        technician_id=appointment.technician_id,
        rating=body.rating,
        comment=body.comment,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return ReviewPublic.model_validate(review)


def notification_filter(user_id: uuid.UUID):
    customer_ids = select(Customer.id).where(Customer.user_id == user_id)
    return or_(
        Notification.user_id == user_id, col(Notification.customer_id).in_(customer_ids)
    )


@router.get("/notifications", response_model=NotificationsPage)
def read_notifications(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> NotificationsPage:
    scope = notification_filter(current_user.id)
    rows = session.exec(
        select(Notification)
        .where(scope)
        .order_by(col(Notification.created_at).desc())
        .offset(skip)
        .limit(limit)
    ).all()
    count = session.exec(
        select(func.count()).select_from(Notification).where(scope)
    ).one()
    unread = session.exec(
        select(func.count())
        .select_from(Notification)
        .where(scope, col(Notification.is_read).is_(False))
    ).one()
    return NotificationsPage(
        data=[NotificationPublic.model_validate(row) for row in rows],
        count=count,
        unread_count=unread,
    )


@router.patch(
    "/notifications/{notification_id}/read", response_model=NotificationPublic
)
def mark_notification_read(
    session: SessionDep, current_user: CurrentUser, notification_id: uuid.UUID
) -> NotificationPublic:
    notification = session.exec(
        select(Notification).where(
            Notification.id == notification_id,
            notification_filter(current_user.id),
        )
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")
    notification.is_read = True
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return NotificationPublic.model_validate(notification)
