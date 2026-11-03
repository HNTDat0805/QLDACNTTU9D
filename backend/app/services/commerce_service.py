import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlmodel import Session, col, func, select

from app.models import (
    Appointment,
    Customer,
    Invoice,
    InvoiceItem,
    InvoiceItemPublic,
    Notification,
    Payment,
    PaymentPublic,
    Quote,
    QuoteItem,
    RepairStatusHistory,
    User,
    get_datetime_utc,
)
from app.schemas.commerce import (
    InvoiceDetail,
    InvoicesPage,
    MonthRevenue,
    PaymentRecord,
    StatisticsResponse,
)
from app.services.access_service import accessible_appointment_ids, is_reception


def check_billing_role(user: User) -> None:
    if not is_reception(user) and user.role != "customer":
        raise HTTPException(status_code=403, detail="Không đủ quyền xem thanh toán")


def invoice_detail(session: Session, invoice: Invoice) -> InvoiceDetail:
    payments = session.exec(
        select(Payment).where(Payment.invoice_id == invoice.id)
    ).all()
    paid = sum(
        (Decimal(str(p.amount)) for p in payments if p.payment_status == "SUCCESS"),
        Decimal(0),
    )
    items = session.exec(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    ).all()
    return InvoiceDetail(
        **invoice.model_dump(),
        items=[InvoiceItemPublic.model_validate(item) for item in items],
        payments=[PaymentPublic.model_validate(p) for p in payments],
        paid_amount=float(paid),
        balance=float(Decimal(str(invoice.total_amount)) - paid),
    )


def ensure_invoice_for_appointment(
    session: Session,
    appointment: Appointment,
) -> Invoice:
    """Đảm bảo đơn sửa chữa đã hoàn thành (COMPLETED) luôn có hóa đơn và thanh toán đầy đủ."""
    if (appointment.status or "").upper() != "COMPLETED":
        raise ValueError(
            "Chỉ tạo hóa đơn tự động cho đơn sửa chữa đã hoàn tất (COMPLETED)"
        )

    invoice = session.exec(
        select(Invoice).where(Invoice.appointment_id == appointment.id)
    ).first()
    if invoice:
        return invoice

    # 1. Đảm bảo báo giá tồn tại và đã duyệt
    from app.services.quote_service import ensure_quote_for_appointment

    quote = ensure_quote_for_appointment(session, appointment)
    if quote.status != "ACCEPTED":
        quote.status = "ACCEPTED"
        session.add(quote)

    # 2. Tạo hóa đơn
    total_amount = float(quote.total_amount or appointment.total_amount or 500000.0)
    now = (
        appointment.actual_completion_date
        or appointment.updated_at
        or get_datetime_utc()
    )

    invoice = Invoice(
        invoice_number=f"INV-{uuid.uuid4().hex[:20].upper()}",
        appointment_id=appointment.id,
        customer_id=appointment.customer_id,
        subtotal=total_amount,
        total_amount=total_amount,
        status="PAID",
        issue_date=now,
    )
    session.add(invoice)
    session.flush()

    # 3. Thêm các hạng mục hóa đơn từ QuoteItem
    quote_items = session.exec(
        select(QuoteItem).where(QuoteItem.quote_id == quote.id)
    ).all()
    if quote_items:
        for q_item in quote_items:
            session.add(
                InvoiceItem(
                    invoice_id=invoice.id,
                    item_name=q_item.item_name,
                    unit_price=q_item.unit_price,
                    quantity=q_item.quantity,
                    total_price=q_item.total_price,
                )
            )
    else:
        session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                item_name="Dịch vụ sửa chữa",
                unit_price=total_amount,
                quantity=1,
                total_price=total_amount,
            )
        )

    # 4. Ghi nhận thanh toán hoàn tất (PAID)
    payment = Payment(
        payment_number=f"PAY-{uuid.uuid4().hex[:20].upper()}",
        invoice_id=invoice.id,
        amount=total_amount,
        payment_method="CASH",
        payment_status="SUCCESS",
        paid_at=now,
        notes="Thanh toán hoàn tất tại cửa hàng khi bàn giao máy",
    )
    session.add(payment)

    session.add(
        RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status="COMPLETED",
            new_status="COMPLETED",
            note=f"Tự động lập hóa đơn {invoice.invoice_number} từ {quote.quote_number}",
        )
    )
    return invoice


def read_invoices(session: Session, user: User, skip: int, limit: int) -> InvoicesPage:
    check_billing_role(user)
    ids = accessible_appointment_ids(session, user)

    # Tự động đồng bộ hóa đơn cho tất cả các lịch hẹn COMPLETED chưa có Invoice
    comp_query = select(Appointment).where(Appointment.status == "COMPLETED")
    if ids is not None:
        comp_query = comp_query.where(col(Appointment.id).in_(ids))
    completed_appts = session.exec(comp_query).all()
    created_any = False
    for appt in completed_appts:
        has_inv = session.exec(
            select(Invoice.id).where(Invoice.appointment_id == appt.id)
        ).first()
        if not has_inv:
            ensure_invoice_for_appointment(session, appt)
            created_any = True
    if created_any:
        session.commit()

    query = select(Invoice)
    count = select(func.count()).select_from(Invoice)
    if ids is not None:
        query = query.where(col(Invoice.appointment_id).in_(ids))
        count = count.where(col(Invoice.appointment_id).in_(ids))
    rows = session.exec(
        query.order_by(col(Invoice.issue_date).desc()).offset(skip).limit(limit)
    ).all()
    return InvoicesPage(
        data=[invoice_detail(session, row) for row in rows],
        count=session.exec(count).one(),
    )


def issue_invoice(session: Session, user: User, quote_id: uuid.UUID) -> InvoiceDetail:
    if not is_reception(user):
        raise HTTPException(
            status_code=403, detail="Chỉ nhân viên tiếp nhận được lập hóa đơn"
        )
    quote = session.get(Quote, quote_id)
    if not quote or quote.status != "ACCEPTED":
        raise HTTPException(status_code=409, detail="Cần báo giá đã được duyệt")
    appointment = session.exec(
        select(Appointment)
        .where(Appointment.id == quote.appointment_id)
        .with_for_update()
    ).first()
    if not appointment or appointment.status != "COMPLETED":
        raise HTTPException(
            status_code=409, detail="Chỉ lập hóa đơn sau khi hoàn tất sửa chữa"
        )
    existing = session.exec(
        select(Invoice).where(Invoice.appointment_id == appointment.id)
    ).first()
    if existing:
        return invoice_detail(session, existing)
    invoice = Invoice(
        invoice_number=f"INV-{uuid.uuid4().hex[:20].upper()}",
        appointment_id=appointment.id,
        customer_id=appointment.customer_id,
        subtotal=quote.total_amount,
        total_amount=quote.total_amount,
        status="UNPAID",
    )
    session.add(invoice)
    session.flush()
    for item in session.exec(
        select(QuoteItem).where(QuoteItem.quote_id == quote.id)
    ).all():
        session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                item_name=item.item_name,
                unit_price=item.unit_price,
                quantity=item.quantity,
                total_price=item.total_price,
            )
        )
    session.add(
        RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status=appointment.status,
            new_status=appointment.status,
            changed_by_user_id=user.id,
            note=f"Lập hóa đơn {invoice.invoice_number} từ {quote.quote_number}",
        )
    )
    session.add(
        Notification(
            customer_id=appointment.customer_id,
            title="Hóa đơn sửa chữa",
            message=f"Hóa đơn {invoice.invoice_number} đã được lập. Vui lòng thanh toán tại cửa hàng.",
        )
    )
    session.commit()
    session.refresh(invoice)
    return invoice_detail(session, invoice)


def record_payment(
    session: Session, user: User, invoice_id: uuid.UUID, data: PaymentRecord
) -> InvoiceDetail:
    if not is_reception(user):
        raise HTTPException(
            status_code=403, detail="Chỉ nhân viên tiếp nhận được ghi nhận thanh toán"
        )
    invoice = session.exec(
        select(Invoice).where(Invoice.id == invoice_id).with_for_update()
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")
    existing = session.exec(
        select(Payment).where(
            Payment.invoice_id == invoice.id,
            Payment.transaction_reference == str(data.request_id),
        )
    ).first()
    if existing:
        if (
            Decimal(str(existing.amount)) != data.amount
            or existing.payment_method != data.payment_method
        ):
            raise HTTPException(
                status_code=409, detail="Mã yêu cầu đã được dùng với nội dung khác"
            )
        return invoice_detail(session, invoice)
    current = invoice_detail(session, invoice)
    if (invoice.status or "").upper() in ("CANCELLED", "PAID") or data.amount > Decimal(
        str(current.balance)
    ):
        raise HTTPException(
            status_code=409, detail="Số tiền vượt số dư hoặc hóa đơn đã kết thúc"
        )
    payment = Payment(
        invoice_id=invoice.id,
        payment_number=f"PAY-{uuid.uuid4().hex[:20].upper()}",
        amount=float(data.amount),
        payment_method=data.payment_method,
        transaction_reference=str(data.request_id),
        notes=data.notes,
    )
    session.add(payment)
    invoice.status = (
        "PAID" if data.amount == Decimal(str(current.balance)) else "PARTIALLY_PAID"
    )
    session.add(invoice)
    session.add(
        RepairStatusHistory(
            appointment_id=invoice.appointment_id,
            previous_status="COMPLETED",
            new_status="COMPLETED",
            changed_by_user_id=user.id,
            note=f"Ghi nhận thanh toán {payment.payment_number}: {data.amount}",
        )
    )
    session.add(
        Notification(
            customer_id=invoice.customer_id,
            title="Đã ghi nhận thanh toán",
            message=f"Hóa đơn {invoice.invoice_number} đã nhận thanh toán {data.amount} VNĐ.",
            notification_type="PAYMENT_CONFIRMATION",
        )
    )
    session.commit()
    session.refresh(invoice)
    return invoice_detail(session, invoice)


def statistics(session: Session, start: date, end: date) -> StatisticsResponse:
    if end < start or (end - start).days > 366:
        raise HTTPException(
            status_code=422,
            detail="Khoảng thống kê tối đa 366 ngày, ngày kết thúc phải sau ngày bắt đầu",
        )
    lower = datetime.combine(start, time.min, UTC)
    upper = datetime.combine(end + timedelta(days=1), time.min, UTC)

    def payment_sum(begin: datetime, finish: datetime) -> float:
        return float(
            session.exec(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.payment_status == "SUCCESS",
                    Payment.paid_at >= begin,
                    Payment.paid_at < finish,
                )
            ).one()
        )

    monthly = []
    cursor = start.replace(day=1)
    while cursor <= end:
        next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        monthly.append(
            MonthRevenue(
                month=cursor.strftime("%Y-%m"),
                amount=payment_sum(
                    max(lower, datetime.combine(cursor, time.min, UTC)),
                    min(upper, datetime.combine(next_month, time.min, UTC)),
                ),
            )
        )
        cursor = next_month
    invoice_total = float(
        session.exec(
            select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
                func.upper(Invoice.status) != "CANCELLED"
            )
        ).one()
    )
    all_paid = float(
        session.exec(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Invoice, col(Payment.invoice_id) == col(Invoice.id))
            .where(
                func.upper(Payment.payment_status) == "SUCCESS",
                func.upper(Invoice.status) != "CANCELLED",
            )
        ).one()
    )
    base = (
        select(func.count())
        .select_from(Appointment)
        .where(
            Appointment.appointment_date >= lower, Appointment.appointment_date < upper
        )
    )
    return StatisticsResponse(
        start_date=start,
        end_date=end,
        receipts_total=payment_sum(lower, upper),
        outstanding_total=max(0, invoice_total - all_paid),
        appointment_count=session.exec(base).one(),
        completed_count=session.exec(
            base.where(Appointment.status == "COMPLETED")
        ).one(),
        customer_count=session.exec(select(func.count()).select_from(Customer)).one(),
        monthly_revenue=monthly,
    )
