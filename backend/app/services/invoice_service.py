import secrets
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlmodel import Session, col, func, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    AppointmentService,
    Customer,
    Invoice,
    InvoiceCreateRequest,
    InvoiceDetail,
    InvoiceItem,
    InvoiceItemDetail,
    Payment,
    Quote,
    QuoteItem,
    QuoteStatus,
    RepairStatusHistory,
    Service,
    User,
    get_datetime_utc,
)

logger = get_logger("app.services.invoice_service")


def _round_money(val: float | Decimal) -> Decimal:
    """Làm tròn số tiền đến 2 chữ số thập phân chính xác bằng Decimal."""
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _resolve_repair_order(
    session: Session, identifier: uuid.UUID | str | int
) -> Appointment | None:
    """
    Tìm kiếm phiếu sửa chữa (Appointment) theo UUID, mã số (appointment_number),
    hoặc chuỗi số nguyên.
    """
    if isinstance(identifier, uuid.UUID):
        return session.get(Appointment, identifier)

    val_str = str(identifier).strip()
    try:
        val_uuid = uuid.UUID(val_str)
        appt = session.get(Appointment, val_uuid)
        if appt:
            return appt
    except ValueError, TypeError, AttributeError:
        pass

    # Tìm theo mã appointment_number chính xác
    appt = session.exec(
        select(Appointment).where(Appointment.appointment_number == val_str)
    ).first()
    if appt:
        return appt

    # Tìm linh hoạt với tiền tố APPT- hoặc hậu tố mã
    return session.exec(
        select(Appointment).where(
            or_(
                col(Appointment.appointment_number) == f"APPT-{val_str}",
                col(Appointment.appointment_number).ilike(f"%{val_str}"),
            )
        )
    ).first()


def _resolve_invoice(
    session: Session, identifier: uuid.UUID | str | int
) -> Invoice | None:
    """
    Tìm kiếm hóa đơn (Invoice) theo UUID, mã hóa đơn (invoice_number), hoặc chuỗi số.
    """
    if isinstance(identifier, uuid.UUID):
        return session.get(Invoice, identifier)

    val_str = str(identifier).strip()
    try:
        val_uuid = uuid.UUID(val_str)
        inv = session.get(Invoice, val_uuid)
        if inv:
            return inv
    except ValueError, TypeError, AttributeError:
        pass

    inv = session.exec(select(Invoice).where(Invoice.invoice_number == val_str)).first()
    if inv:
        return inv

    return session.exec(
        select(Invoice).where(
            or_(
                col(Invoice.invoice_number) == f"INV-{val_str}",
                col(Invoice.invoice_number) == f"HD-{val_str}",
                col(Invoice.invoice_number).ilike(f"%{val_str}"),
            )
        )
    ).first()


def generate_invoice_number(session: Session, appointment: Appointment) -> str:
    """
    Sinh mã hóa đơn duy nhất (ví dụ: HD-20261101-ABCD hoặc INV-20261101-ABCD).
    """
    # Lấy ngày hiện tại hoặc ngày hẹn
    date_str = appointment.appointment_date.strftime("%Y%m%d")
    base_suffix = appointment.appointment_number.split("-")[-1]
    candidate = f"HD-{date_str}-{base_suffix}"

    existing = session.exec(
        select(Invoice).where(Invoice.invoice_number == candidate)
    ).first()
    if not existing:
        return candidate

    # Nếu trùng, thử gắn hậu tố phiên bản -v2, -v3...
    for i in range(2, 20):
        v_cand = f"{candidate}-v{i}"
        if not session.exec(
            select(Invoice).where(Invoice.invoice_number == v_cand)
        ).first():
            return v_cand

    # Fallback mã ngẫu nhiên
    for _ in range(10):
        suffix = secrets.token_hex(2).upper()
        random_cand = f"HD-{date_str}-{suffix}"
        if not session.exec(
            select(Invoice).where(Invoice.invoice_number == random_cand)
        ).first():
            return random_cand

    return f"HD-{date_str}-{uuid.uuid4().hex[:6].upper()}"


def _build_invoice_detail(session: Session, invoice: Invoice) -> InvoiceDetail:
    """
    Chuyển đổi thực thể Invoice và dữ liệu liên quan thành InvoiceDetail đầy đủ.
    """
    appointment = session.get(Appointment, invoice.appointment_id)
    customer = session.get(Customer, invoice.customer_id)

    # Lấy các hạng mục hóa đơn
    items_data = session.exec(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    ).all()
    items_detail = [
        InvoiceItemDetail(
            id=item.id,
            item_name=item.item_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
        )
        for item in items_data
    ]

    # Tính tổng tiền đã thanh toán từ các giao dịch thành công
    payments = session.exec(
        select(Payment).where(
            Payment.invoice_id == invoice.id,
            col(Payment.payment_status).in_(["SUCCESS", "completed", "SUCCESSFUL"]),
        )
    ).all()
    paid_total = sum(p.amount for p in payments)
    remaining = max(0.0, invoice.total_amount - paid_total)

    return InvoiceDetail(
        id=invoice.id,
        invoice_code=invoice.invoice_number,
        invoice_number=invoice.invoice_number,
        repair_order_id=invoice.appointment_id,
        appointment_number=appointment.appointment_number if appointment else "",
        customer_id=invoice.customer_id,
        customer_name=customer.full_name if customer else "Khách hàng",
        customer_phone=customer.phone_number if customer else None,
        subtotal=invoice.subtotal,
        discount_amount=invoice.discount_amount,
        tax_amount=invoice.tax_amount,
        total_amount=invoice.total_amount,
        paid_amount=paid_total,
        remaining_amount=remaining,
        status=(invoice.status or "unpaid").lower(),
        items=items_detail,
        created_at=invoice.created_at,
        notes=invoice.notes,
    )


def create_invoice_for_repair_order(
    session: Session,
    data: InvoiceCreateRequest,
    current_user: User,
) -> InvoiceDetail:
    """
    Tạo hóa đơn cho đơn sửa chữa (Task 315):
    - Khóa dòng phiếu sửa chữa bằng with_for_update() để chống tranh chấp đồng thời.
    - Kiểm tra đơn sửa chữa tồn tại (404 Not Found).
    - Kiểm tra trạng thái đơn sửa chữa (chặn nếu đã CANCELLED -> 400 Bad Request).
    - Kiểm tra tính duy nhất: Chặn tạo trùng lặp hóa đơn cho cùng một đơn sửa chữa (409 Conflict).
    - Lấy thông tin khách hàng từ đơn sửa chữa.
    - Lấy danh sách dịch vụ và hạng mục sửa chữa đã được xác nhận:
      + Ưu tiên 1: Lấy từ báo giá đã được duyệt (Quote có status=ACCEPTED).
      + Ưu tiên 2: Lấy từ danh sách dịch vụ gắn với lịch hẹn (AppointmentService).
    - Tính toán tổng tiền hoàn toàn ở backend (dùng Decimal), không tin tưởng số tiền từ client.
    - Lưu hóa đơn và các InvoiceItem trong cùng một database transaction.
    - Ghi nhận lịch sử vào RepairStatusHistory.
    """
    logger.info(
        f"Bắt đầu tạo hóa đơn cho repair_order={data.repair_order_id} bởi user={current_user.id}"
    )

    now = get_datetime_utc()

    try:
        # 1. Tìm đơn sửa chữa
        appointment = _resolve_repair_order(session, data.repair_order_id)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy đơn sửa chữa với định danh: {data.repair_order_id}",
            )

        # Khóa dòng để tránh tạo đồng thời 2 hóa đơn
        locked_appt = session.exec(
            select(Appointment)
            .where(Appointment.id == appointment.id)
            .with_for_update()
        ).first()
        if not locked_appt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Đơn sửa chữa không còn tồn tại.",
            )
        appointment = locked_appt

        # 2. Kiểm tra trạng thái đơn sửa chữa
        appt_status = (appointment.status or "").upper()
        if appt_status == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể tạo hóa đơn cho đơn sửa chữa đã bị hủy (Mã: {appointment.appointment_number}).",
            )

        # 3. Chống tạo hóa đơn trùng lặp
        existing_invoice = session.exec(
            select(Invoice).where(Invoice.appointment_id == appointment.id)
        ).first()
        if existing_invoice:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Đơn sửa chữa {appointment.appointment_number} đã có hóa đơn "
                    f"(Mã hóa đơn: {existing_invoice.invoice_number}). Không thể tạo trùng lặp."
                ),
            )

        # 4. Thu thập các hạng mục sửa chữa đã xác nhận
        prepared_items: list[dict[str, Any]] = []

        # Ưu tiên kiểm tra báo giá đã duyệt (Quote status == ACCEPTED)
        accepted_quote = session.exec(
            select(Quote)
            .where(
                Quote.appointment_id == appointment.id,
                Quote.status == QuoteStatus.ACCEPTED.value,
            )
            .order_by(col(Quote.updated_at).desc(), col(Quote.created_at).desc())
        ).first()

        if accepted_quote:
            quote_items = session.exec(
                select(QuoteItem).where(QuoteItem.quote_id == accepted_quote.id)
            ).all()
            for q_item in quote_items:
                item_qty = q_item.quantity if q_item.quantity > 0 else 1
                item_price = _round_money(q_item.unit_price)
                item_total = _round_money(item_price * item_qty)
                prepared_items.append(
                    {
                        "item_name": q_item.item_name,
                        "unit_price": float(item_price),
                        "quantity": item_qty,
                        "total_price": item_total,
                    }
                )

        # Nếu không có báo giá duyệt, lấy từ danh sách dịch vụ đăng ký (AppointmentService)
        if not prepared_items:
            services = session.exec(
                select(AppointmentService, Service)
                .join(Service, col(AppointmentService.service_id) == col(Service.id))
                .where(AppointmentService.appointment_id == appointment.id)
            ).all()

            for appt_svc, svc in services:
                item_qty = appt_svc.quantity if appt_svc.quantity > 0 else 1
                item_price = _round_money(appt_svc.price_at_booking)
                item_total = _round_money(item_price * item_qty)
                prepared_items.append(
                    {
                        "item_name": svc.name,
                        "unit_price": float(item_price),
                        "quantity": item_qty,
                        "total_price": item_total,
                    }
                )

        # 5. Nếu không có bất kỳ hạng mục nào, từ chối tạo hóa đơn
        if not prepared_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Đơn sửa chữa {appointment.appointment_number} chưa có hạng mục dịch vụ "
                    "hoặc báo giá đã xác nhận nào để lập hóa đơn."
                ),
            )

        # 6. Tính toán tổng tiền ở backend (sử dụng Decimal)
        subtotal_decimal = sum(item["total_price"] for item in prepared_items)
        if subtotal_decimal <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tổng tiền hóa đơn tính toán được phải lớn hơn 0.",
            )

        subtotal_float = float(subtotal_decimal)
        total_amount_float = subtotal_float

        # 7. Sinh mã hóa đơn duy nhất
        invoice_code = generate_invoice_number(session, appointment)

        # 8. Khởi tạo đối tượng hóa đơn
        invoice = Invoice(
            id=uuid.uuid4(),
            invoice_number=invoice_code,
            appointment_id=appointment.id,
            customer_id=appointment.customer_id,
            subtotal=subtotal_float,
            discount_amount=0.0,
            tax_amount=0.0,
            total_amount=total_amount_float,
            status="unpaid",
            issue_date=now,
            due_date=None,
            notes=data.notes.strip() if data.notes else None,
            created_at=now,
            updated_at=now,
        )
        session.add(invoice)
        session.flush()

        # 9. Lưu các InvoiceItem
        for p_item in prepared_items:
            item_record = InvoiceItem(
                id=uuid.uuid4(),
                invoice_id=invoice.id,
                item_name=p_item["item_name"],
                unit_price=p_item["unit_price"],
                quantity=p_item["quantity"],
                total_price=float(p_item["total_price"]),
            )
            session.add(item_record)

        # 10. Ghi nhận lịch sử kiểm toán vào RepairStatusHistory
        creator_name = current_user.full_name or current_user.email
        audit_history = RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status=appointment.status,
            new_status=appointment.status,
            note=(
                f"Lập hóa đơn {invoice.invoice_number} (tổng tiền: {invoice.total_amount:,.0f} đ) "
                f"bởi {creator_name}"
            ),
            changed_by_user_id=current_user.id,
            created_at=now,
        )
        session.add(audit_history)

        # 11. Hoàn tất giao dịch
        session.commit()
        session.refresh(invoice)

        logger.info(
            f"Tạo hóa đơn thành công: {invoice.invoice_number} cho đơn {appointment.appointment_number} "
            f"với {len(prepared_items)} hạng mục, tổng tiền {invoice.total_amount:,.0f} đ"
        )

        return _build_invoice_detail(session, invoice)

    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        logger.error(
            f"Lỗi không xác định khi tạo hóa đơn cho đơn sửa chữa: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra lỗi trong quá trình tạo hóa đơn. Vui lòng thử lại sau.",
        ) from exc


def get_invoice_by_id(
    session: Session,
    invoice_id: uuid.UUID | str,
    current_user: User | None = None,
) -> InvoiceDetail:
    """Lấy thông tin chi tiết một hóa đơn."""
    _ = current_user
    invoice = _resolve_invoice(session, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy hóa đơn với định danh: {invoice_id}",
        )
    return _build_invoice_detail(session, invoice)


def list_invoices(
    session: Session,
    skip: int = 0,
    limit: int = 20,
    status_filter: str | None = None,
    customer_id: uuid.UUID | None = None,
) -> tuple[list[InvoiceDetail], int]:
    """Danh sách hóa đơn phân trang với bộ lọc."""
    query = select(Invoice)
    count_query = select(func.count()).select_from(Invoice)
    if status_filter:
        normalized_status = status_filter.strip().upper()
        query = query.where(func.upper(Invoice.status) == normalized_status)
        count_query = count_query.where(func.upper(Invoice.status) == normalized_status)
    if customer_id:
        query = query.where(Invoice.customer_id == customer_id)
        count_query = count_query.where(Invoice.customer_id == customer_id)

    total_count = int(session.exec(count_query).one())

    query = query.order_by(col(Invoice.created_at).desc()).offset(skip).limit(limit)
    invoices = session.exec(query).all()

    details = [_build_invoice_detail(session, inv) for inv in invoices]
    return details, total_count
