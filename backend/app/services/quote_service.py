import secrets
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import TypedDict

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    Customer,
    Device,
    QuotationCreate,
    QuotationDetail,
    QuotationItemDetail,
    Quote,
    QuoteItem,
    QuoteStatus,
    RepairStatusHistory,
    Service,
    User,
    get_datetime_utc,
)

logger = get_logger("app.services.quote_service")


class PreparedQuoteItem(TypedDict):
    service_id: uuid.UUID | None
    item_name: str
    unit_price: float
    quantity: int
    total_price: float
    notes: str | None


def _round_money(val: float | Decimal) -> Decimal:
    """Làm tròn số tiền đến 2 chữ số thập phân chính xác bằng Decimal."""
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _build_quotation_detail(session: Session, quote: Quote) -> QuotationDetail:
    """Helper chuyển đổi thực thể Quote và các liên kết thành QuotationDetail."""
    appointment = session.get(Appointment, quote.appointment_id)
    customer = session.get(Customer, appointment.customer_id) if appointment else None
    device = session.get(Device, appointment.device_id) if appointment else None

    items_data = session.exec(
        select(QuoteItem).where(QuoteItem.quote_id == quote.id)
    ).all()

    items_detail = [
        QuotationItemDetail(
            id=item.id,
            service_id=item.service_id,
            item_name=item.item_name,
            unit_price=item.unit_price,
            quantity=item.quantity,
            total_price=item.total_price,
            notes=item.notes,
        )
        for item in items_data
    ]

    device_info_str = f"{device.brand} {device.model}".strip() if device else "Không rõ"

    return QuotationDetail(
        id=quote.id,
        quote_number=quote.quote_number,
        appointment_id=quote.appointment_id,
        appointment_number=(appointment.appointment_number if appointment else ""),
        customer_id=appointment.customer_id if appointment else uuid.uuid4(),
        customer_name=customer.full_name if customer else "Khách hàng",
        customer_phone=customer.phone_number if customer else "",
        device_info=device_info_str,
        total_amount=quote.total_amount,
        status=quote.status,
        valid_until=quote.valid_until,
        customer_notes=quote.customer_notes,
        items=items_detail,
        created_at=quote.created_at,
        updated_at=quote.updated_at,
    )


def generate_quote_number(session: Session, appointment: Appointment) -> str:
    """
    Sinh mã báo giá duy nhất cho phiếu sửa chữa:
    - Ưu tiên: Chuyển đổi mã lịch hẹn APPT-YYYYMMDD-XXXX thành QUO-YYYYMMDD-XXXX.
    - Nếu đã tồn tại báo giá với mã này, sinh hậu tố version: QUO-YYYYMMDD-XXXX-v2...
    - Fallback: Sinh mã ngẫu nhiên theo ngày QUO-YYYYMMDD-XXXX.
    """
    base_code = appointment.appointment_number.replace("APPT", "QUO")
    existing = session.exec(
        select(Quote).where(Quote.quote_number == base_code)
    ).first()
    if not existing:
        return base_code

    for i in range(2, 20):
        candidate = f"{base_code}-v{i}"
        if not session.exec(
            select(Quote).where(Quote.quote_number == candidate)
        ).first():
            return candidate

    date_str = appointment.appointment_date.strftime("%Y%m%d")
    for _ in range(10):
        suffix = secrets.token_hex(2).upper()
        candidate = f"QUO-{date_str}-{suffix}"
        if not session.exec(
            select(Quote).where(Quote.quote_number == candidate)
        ).first():
            return candidate

    return f"QUO-{date_str}-{uuid.uuid4().hex[:6].upper()}"


def create_repair_quotation(
    session: Session,
    quote_in: QuotationCreate,
    current_user: User,
) -> QuotationDetail:
    """
    Tạo báo giá sửa chữa mới cho phiếu sửa chữa (Appointment):
    - Kiểm tra phiếu sửa chữa tồn tại và ở trạng thái hợp lệ.
    - Xác minh các dịch vụ tham chiếu từ danh mục (nếu có).
    - Tính toán thành tiền từng hạng mục và tổng tiền hoàn toàn ở backend (Decimal chính xác).
    - Lưu báo giá và các hạng mục bằng transaction an toàn.
    """
    logger.info(
        f"Bắt đầu tạo báo giá sửa chữa bởi user={current_user.id} ({current_user.email})"
    )

    now = get_datetime_utc()

    try:
        # 1. Tìm phiếu sửa chữa (Appointment)
        appointment: Appointment | None = None
        if quote_in.appointment_id:
            appointment = session.get(Appointment, quote_in.appointment_id)
        elif quote_in.appointment_number:
            appointment = session.exec(
                select(Appointment).where(
                    Appointment.appointment_number
                    == quote_in.appointment_number.strip()
                )
            ).first()

        if not appointment:
            identifier = quote_in.appointment_id or quote_in.appointment_number
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy phiếu sửa chữa với định danh: {identifier}",
            )

        # 2. Kiểm tra trạng thái phiếu sửa chữa
        if appointment.status == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Phiếu sửa chữa {appointment.appointment_number} đã bị hủy, không thể tạo báo giá",
            )
        if appointment.status == "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Phiếu sửa chữa {appointment.appointment_number} đã hoàn thành, không thể tạo báo giá mới",
            )

        # 3. Duyệt và xác thực từng hạng mục báo giá (Items)
        prepared_items: list[PreparedQuoteItem] = []
        total_amount_dec = Decimal("0.00")

        for idx, item in enumerate(quote_in.items, start=1):
            service: Service | None = None
            if item.service_id:
                service = session.get(Service, item.service_id)
                if not service:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Hạng mục {idx}: Không tìm thấy dịch vụ sửa chữa với ID {item.service_id}",
                    )

            # Xác định tên hạng mục
            item_name = item.item_name
            if not item_name:
                if service:
                    item_name = service.name
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Hạng mục {idx}: Cần cung cấp tên hạng mục (item_name) nếu không chọn dịch vụ từ danh mục",
                    )

            # Xác định đơn giá
            unit_price = item.unit_price
            if unit_price is None:
                if service:
                    unit_price = service.base_price
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Hạng mục {idx}: Cần cung cấp đơn giá (unit_price) nếu không chọn dịch vụ từ danh mục",
                    )

            if unit_price < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Hạng mục {idx}: Đơn giá không được âm",
                )
            if item.quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Hạng mục {idx}: Số lượng phải lớn hơn 0",
                )

            # Tính toán tiền tệ với Decimal để tránh sai số dấu phẩy động
            price_dec = _round_money(unit_price)
            qty_dec = Decimal(str(item.quantity))
            item_total_dec = _round_money(price_dec * qty_dec)
            total_amount_dec += item_total_dec

            prepared_items.append(
                PreparedQuoteItem(
                    service_id=service.id if service else None,
                    item_name=item_name,
                    unit_price=float(price_dec),
                    quantity=item.quantity,
                    total_price=float(item_total_dec),
                    notes=item.notes.strip() if item.notes else None,
                )
            )

        # 4. Sinh mã báo giá
        quote_number = generate_quote_number(session, appointment)

        # 5. Khởi tạo đối tượng Quote
        quote = Quote(
            id=uuid.uuid4(),
            quote_number=quote_number,
            appointment_id=appointment.id,
            total_amount=float(total_amount_dec),
            status=quote_in.status.value,
            valid_until=quote_in.valid_until,
            customer_notes=(
                quote_in.customer_notes.strip() if quote_in.customer_notes else None
            ),
            created_at=now,
            updated_at=now,
        )
        session.add(quote)
        session.flush()

        # 6. Khởi tạo và lưu từng QuoteItem
        for p_item in prepared_items:
            db_item = QuoteItem(
                id=uuid.uuid4(),
                quote_id=quote.id,
                service_id=p_item["service_id"],
                item_name=p_item["item_name"],
                unit_price=p_item["unit_price"],
                quantity=p_item["quantity"],
                total_price=p_item["total_price"],
                notes=p_item["notes"],
            )
            session.add(db_item)

        session.commit()
        session.refresh(quote)

        logger.info(
            f"Tạo báo giá thành công: {quote.quote_number} cho lịch hẹn {appointment.appointment_number} với tổng tiền {quote.total_amount}"
        )

        return _build_quotation_detail(session, quote)

    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        logger.error(
            f"Lỗi không xác định khi tạo báo giá sửa chữa: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra lỗi trong quá trình tạo báo giá sửa chữa. Vui lòng thử lại sau.",
        ) from exc


def accept_quotation(
    session: Session,
    quote_id: uuid.UUID,
    current_user: User,
    note: str | None = None,
) -> QuotationDetail:
    """
    Duyệt báo giá sửa chữa (Quotation Approval):
    - Sử dụng with_for_update() khóa dòng để tránh race condition hoặc duyệt lặp đồng thời.
    - Kiểm tra báo giá có tồn tại (404 nếu không tìm thấy).
    - Kiểm tra trạng thái hiện tại (chỉ DRAFT hoặc SENT mới được duyệt; nếu đã ACCEPTED -> 409 Conflict; REJECTED -> 409 Conflict).
    - Kiểm tra phân quyền:
      + Staff / Technician / Manager / Admin: được duyệt.
      + Customer: chỉ được duyệt báo giá thuộc phiếu sửa chữa của chính mình (403 nếu không phải chủ sở hữu).
    - Cập nhật trạng thái báo giá sang ACCEPTED.
    - Ghi nhận lịch sử kiểm toán vào RepairStatusHistory.
    - Transaction an toàn, commit và trả về QuotationDetail.
    """
    logger.info(
        f"Bắt đầu duyệt báo giá quote_id={quote_id} bởi user={current_user.id} ({current_user.email})"
    )

    now = get_datetime_utc()

    try:
        # 1. Tìm báo giá với khóa bi quan (with_for_update) để ngăn chặn race condition đồng thời
        quote = session.exec(
            select(Quote).where(Quote.id == quote_id).with_for_update()
        ).first()

        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy báo giá với ID: {quote_id}",
            )

        # 2. Lấy thông tin phiếu sửa chữa
        appointment = session.get(Appointment, quote.appointment_id)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiếu sửa chữa liên quan đến báo giá này",
            )

        # 3. Kiểm tra trạng thái hiện tại của báo giá
        if quote.status == QuoteStatus.ACCEPTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Báo giá {quote.quote_number} đã được duyệt trước đó",
            )
        if quote.status == QuoteStatus.REJECTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Báo giá {quote.quote_number} đã bị từ chối, không thể duyệt",
            )
        if quote.status not in (QuoteStatus.DRAFT.value, QuoteStatus.SENT.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Báo giá đang ở trạng thái '{quote.status}', không thể duyệt",
            )

        # 4. Kiểm tra phân quyền: Nhân viên hoặc Khách hàng sở hữu
        is_staff_or_admin = current_user.is_superuser or (
            (current_user.role or "").lower()
            in ["admin", "manager", "staff", "technician"]
        )

        if not is_staff_or_admin:
            # Người dùng là customer, chỉ được duyệt báo giá của chính mình
            customer = session.get(Customer, appointment.customer_id)
            is_owner = False
            if customer:
                if customer.user_id and customer.user_id == current_user.id:
                    is_owner = True
                elif (
                    customer.email
                    and customer.email.strip().lower()
                    == current_user.email.strip().lower()
                ):
                    is_owner = True

            if not is_owner:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền duyệt báo giá của khách hàng khác",
                )

        # 5. Cập nhật trạng thái báo giá sang ACCEPTED
        quote.status = QuoteStatus.ACCEPTED.value
        quote.updated_at = now
        if note and note.strip():
            note_str = note.strip()
            if quote.customer_notes:
                quote.customer_notes = (
                    f"{quote.customer_notes}\n[Ghi chú duyệt]: {note_str}"
                )
            else:
                quote.customer_notes = f"[Ghi chú duyệt]: {note_str}"

        session.add(quote)

        # 6. Ghi nhận nhật ký audit trail vào RepairStatusHistory (không làm đổi trạng thái sửa chữa của Appointment)
        approver_display = current_user.full_name or current_user.email
        audit_note_parts = [
            f"Báo giá {quote.quote_number} (tổng tiền: {quote.total_amount:,.0f} đ) đã được duyệt bởi {approver_display}"
        ]
        if note and note.strip():
            audit_note_parts.append(f"Ghi chú: {note.strip()}")

        status_history = RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status=appointment.status,
            new_status=appointment.status,
            note=". ".join(audit_note_parts),
            changed_by_user_id=current_user.id,
        )
        session.add(status_history)

        session.commit()
        session.refresh(quote)

        logger.info(
            f"Duyệt báo giá thành công: {quote.quote_number} (ID: {quote.id}) sang trạng thái ACCEPTED"
        )

        return _build_quotation_detail(session, quote)

    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        logger.error(
            f"Lỗi không xác định khi duyệt báo giá sửa chữa: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra lỗi trong quá trình duyệt báo giá sửa chữa. Vui lòng thử lại sau.",
        ) from exc
