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

        # Lấy thông tin khách hàng và thiết bị để trả về chi tiết báo giá
        customer = session.get(Customer, appointment.customer_id)
        device = session.get(Device, appointment.device_id)

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
        items_detail: list[QuotationItemDetail] = []
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
            items_detail.append(
                QuotationItemDetail(
                    id=db_item.id,
                    service_id=db_item.service_id,
                    item_name=db_item.item_name,
                    unit_price=db_item.unit_price,
                    quantity=db_item.quantity,
                    total_price=db_item.total_price,
                    notes=db_item.notes,
                )
            )

        session.commit()
        session.refresh(quote)

        logger.info(
            f"Tạo báo giá thành công: {quote.quote_number} cho lịch hẹn {appointment.appointment_number} với tổng tiền {quote.total_amount}"
        )

        device_info_str = (
            f"{device.brand} {device.model}".strip() if device else "Không rõ"
        )

        return QuotationDetail(
            id=quote.id,
            quote_number=quote.quote_number,
            appointment_id=appointment.id,
            appointment_number=appointment.appointment_number,
            customer_id=appointment.customer_id,
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
