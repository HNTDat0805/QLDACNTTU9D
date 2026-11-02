import secrets
import uuid
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlmodel import Session, col, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    Invoice,
    Payment,
    PaymentCreateRequest,
    PaymentDetail,
    PaymentMethod,
    RepairStatusHistory,
    SystemLog,
    User,
    get_datetime_utc,
)
from app.services.invoice_service import _resolve_invoice

logger = get_logger("app.services.payment_service")


def _round_money(val: float | Decimal) -> Decimal:
    """Làm tròn số tiền đến 2 chữ số thập phân chính xác bằng Decimal."""
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _normalize_payment_method(val: str) -> str:
    """
    Chuẩn hóa phương thức thanh toán sang giá trị chuẩn FixPhone.
    Hỗ trợ cả tiếng Việt không dấu, có dấu và tên tiếng Anh.
    """
    cleaned = val.strip().lower()
    mapping = {
        "cash": PaymentMethod.CASH.value,
        "tien_mat": PaymentMethod.CASH.value,
        "tiền mặt": PaymentMethod.CASH.value,
        "cod": PaymentMethod.COD.value,
        "thanh_toan_khi_nhan_may": PaymentMethod.COD.value,
        "khi nhận máy": PaymentMethod.COD.value,
        "nhận máy": PaymentMethod.COD.value,
        "bank_transfer": PaymentMethod.BANK_TRANSFER.value,
        "chuyen_khoan": PaymentMethod.BANK_TRANSFER.value,
        "chuyển khoản": PaymentMethod.BANK_TRANSFER.value,
        "qr": PaymentMethod.BANK_TRANSFER.value,
        "chuyen_khoan_qr": PaymentMethod.BANK_TRANSFER.value,
        "card": PaymentMethod.CARD.value,
        "the_atm": PaymentMethod.CARD.value,
        "atm": PaymentMethod.CARD.value,
        "visa": PaymentMethod.CARD.value,
        "mastercard": PaymentMethod.CARD.value,
        "credit_card": PaymentMethod.CARD.value,
        "the": PaymentMethod.CARD.value,
        "thẻ": PaymentMethod.CARD.value,
        "e_wallet": PaymentMethod.E_WALLET.value,
        "vi_dien_tu": PaymentMethod.E_WALLET.value,
        "ví điện tử": PaymentMethod.E_WALLET.value,
        "momo": PaymentMethod.E_WALLET.value,
        "vnpay": PaymentMethod.E_WALLET.value,
        "zalopay": PaymentMethod.E_WALLET.value,
    }

    if cleaned in mapping:
        return mapping[cleaned]

    for member in PaymentMethod:
        if cleaned == member.value.lower():
            return member.value

    valid_methods = ", ".join([m.value for m in PaymentMethod])
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Phương thức thanh toán '{val}' không hợp lệ. Các phương thức hỗ trợ: {valid_methods}",
    )


def generate_payment_number(session: Session, _invoice: Invoice | None = None) -> str:
    """
    Sinh mã giao dịch thanh toán duy nhất (PAY-YYYYMMDD-XXXX).
    """
    now = get_datetime_utc()
    date_str = now.strftime("%Y%m%d")
    base_prefix = f"PAY-{date_str}"

    for _ in range(20):
        suffix = secrets.token_hex(2).upper()
        candidate = f"{base_prefix}-{suffix}"
        if not session.exec(
            select(Payment).where(Payment.payment_number == candidate)
        ).first():
            return candidate

    return f"{base_prefix}-{uuid.uuid4().hex[:6].upper()}"


def _build_payment_detail(
    session: Session,
    payment: Payment,
    invoice: Invoice | None = None,
    current_user: User | None = None,
) -> PaymentDetail:
    """Xây dựng dữ liệu chi tiết cho response thanh toán."""
    if not invoice:
        invoice = session.get(Invoice, payment.invoice_id)

    # Tính lại tổng đã thanh toán và còn nợ của hóa đơn
    invoice_code = invoice.invoice_number if invoice else "HD-UNKNOWN"
    current_inv_status = (invoice.status or "unpaid").lower() if invoice else "unpaid"

    remaining = 0.0
    if invoice:
        all_payments = session.exec(
            select(Payment).where(
                Payment.invoice_id == invoice.id,
                col(Payment.payment_status).in_(["SUCCESS", "completed", "SUCCESSFUL"]),
            )
        ).all()
        paid_sum = sum(p.amount for p in all_payments)
        remaining = max(0.0, invoice.total_amount - paid_sum)

    # Trích xuất người ghi nhận từ notes hoặc current_user
    recorded_by = None
    if current_user:
        recorded_by = current_user.full_name or current_user.email
    elif payment.notes and "[Ghi nhận bởi:" in payment.notes:
        try:
            parts = payment.notes.split("[Ghi nhận bởi:")
            if len(parts) > 1:
                recorded_by = parts[1].split("]")[0].strip()
        except Exception:
            pass

    return PaymentDetail(
        id=payment.id,
        payment_code=payment.payment_number,
        payment_number=payment.payment_number,
        invoice_id=payment.invoice_id,
        invoice_code=invoice_code,
        amount=payment.amount,
        payment_method=payment.payment_method,
        status="completed"
        if payment.payment_status in ("SUCCESS", "completed")
        else "pending",
        paid_at=payment.paid_at,
        transaction_code=payment.transaction_reference,
        transaction_reference=payment.transaction_reference,
        recorded_by=recorded_by,
        recorded_by_user_id=current_user.id if current_user else None,
        note=payment.notes,
        created_at=payment.created_at,
        invoice_status_after_payment=current_inv_status,
        invoice_remaining_amount=remaining,
    )


def record_payment(
    session: Session,
    data: PaymentCreateRequest,
    current_user: User,
) -> PaymentDetail:
    """
    Ghi nhận thanh toán cho hóa đơn (Task 319):
    - Khóa dòng hóa đơn (with_for_update) chống xung đột cập nhật đồng thời.
    - Kiểm tra hóa đơn tồn tại (404 Not Found).
    - Kiểm tra trạng thái hóa đơn:
      + Đã hủy -> 400 Bad Request.
      + Đã thanh toán đầy đủ -> 400 Bad Request.
    - Kiểm tra số tiền thanh toán:
      + Phải > 0 (400 Bad Request).
      + Không vượt quá số tiền còn phải thanh toán (400 Bad Request).
    - Hỗ trợ thanh toán nhiều lần:
      + Chưa đủ -> partially_paid.
      + Đủ hoặc hết nợ -> paid.
    - Chống thanh toán trùng lặp:
      + Trùng transaction_code đã ghi nhận -> 409 Conflict.
      + Giao dịch lặp lại trong vòng 60 giây cùng số tiền và phương thức -> 409 Conflict.
    - Xác minh phương thức thanh toán:
      + Tiền mặt / COD: hợp lệ trực tiếp tại quầy hoặc khi nhận máy.
      + Chuyển khoản, QR, Thẻ, Ví điện tử: yêu cầu có mã giao dịch hoặc ghi chú xác minh từ nhân viên.
    - Thực hiện ghi nhận thanh toán và cập nhật trạng thái hóa đơn trong cùng một transaction.
    - Rollback toàn bộ nếu có lỗi.
    """
    logger.info(
        f"Bắt đầu ghi nhận thanh toán cho hóa đơn {data.invoice_id}, "
        f"số tiền: {data.amount}, phương thức: {data.payment_method} bởi user={current_user.id}"
    )

    now = get_datetime_utc()

    try:
        # 1. Tìm kiếm hóa đơn
        invoice = _resolve_invoice(session, data.invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy hóa đơn với định danh: {data.invoice_id}",
            )

        # 2. Khóa dòng hóa đơn để bảo vệ tính toàn vẹn tài chính trong transaction
        locked_inv = session.exec(
            select(Invoice).where(Invoice.id == invoice.id).with_for_update()
        ).first()
        if not locked_inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hóa đơn không còn tồn tại.",
            )
        invoice = locked_inv

        # 3. Kiểm tra trạng thái hóa đơn
        inv_status = (invoice.status or "").lower()
        if inv_status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hóa đơn {invoice.invoice_number} đã bị hủy, không thể ghi nhận thanh toán.",
            )
        if inv_status == "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hóa đơn {invoice.invoice_number} đã được thanh toán đầy đủ trước đó.",
            )

        # 4. Kiểm tra số tiền thanh toán
        amount_decimal = _round_money(Decimal(str(data.amount)))
        if amount_decimal <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Số tiền thanh toán phải lớn hơn 0.",
            )

        # 5. Kiểm tra số tiền còn nợ
        existing_payments = session.exec(
            select(Payment).where(
                Payment.invoice_id == invoice.id,
                col(Payment.payment_status).in_(["SUCCESS", "completed", "SUCCESSFUL"]),
            )
        ).all()
        paid_total_decimal = sum(Decimal(str(p.amount)) for p in existing_payments)
        invoice_total_decimal = Decimal(str(invoice.total_amount))
        remaining_due = invoice_total_decimal - paid_total_decimal

        if remaining_due <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hóa đơn {invoice.invoice_number} đã được thanh toán đầy đủ, không còn số tiền nợ.",
            )

        if amount_decimal > remaining_due:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Số tiền thanh toán ({float(amount_decimal):,.0f} đ) vượt quá số tiền còn nợ "
                    f"({float(remaining_due):,.0f} đ) của hóa đơn {invoice.invoice_number}."
                ),
            )

        # 6. Chuẩn hóa phương thức thanh toán
        normalized_method = _normalize_payment_method(data.payment_method)

        # 7. Kiểm tra xác minh giao dịch phi tiền mặt (Chuyển khoản, QR, Thẻ, Ví điện tử)
        tx_code = data.transaction_code.strip() if data.transaction_code else None
        if normalized_method in (
            PaymentMethod.BANK_TRANSFER.value,
            PaymentMethod.CARD.value,
            PaymentMethod.E_WALLET.value,
        ):
            has_tx = bool(tx_code and len(tx_code) > 0)
            has_valid_note = bool(data.note and len(data.note.strip()) >= 5)
            if not has_tx and not has_valid_note:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Đối với phương thức thanh toán phi tiền mặt ({normalized_method}), "
                        "cần cung cấp mã giao dịch (transaction_code) hoặc ghi chú xác minh "
                        "giao dịch từ nhân viên để đối soát kế toán."
                    ),
                )

        # 8. Chống thanh toán trùng lặp (Anti Duplicate Payment)
        # 8a. Trùng mã tham chiếu giao dịch (nếu có)
        if tx_code:
            duplicate_tx = session.exec(
                select(Payment).where(Payment.transaction_reference == tx_code)
            ).first()
            if duplicate_tx:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Mã giao dịch '{tx_code}' đã được ghi nhận trước đó trên hệ thống "
                        f"(Mã thanh toán: {duplicate_tx.payment_number})."
                    ),
                )

        # 8b. Trùng giao dịch trong thời gian ngắn (60 giây) cho cùng hóa đơn, số tiền và phương thức
        short_time_threshold = now - timedelta(seconds=60)
        recent_duplicate = session.exec(
            select(Payment).where(
                Payment.invoice_id == invoice.id,
                Payment.amount == float(amount_decimal),
                Payment.payment_method == normalized_method,
                col(Payment.created_at) >= short_time_threshold,
            )
        ).first()
        if recent_duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Phát hiện giao dịch tương tự vừa được ghi nhận trong vòng 60 giây. "
                    "Vui lòng kiểm tra lại để tránh thanh toán trùng lặp."
                ),
            )

        # 9. Xác định trạng thái hóa đơn mới sau giao dịch
        new_paid_total = paid_total_decimal + amount_decimal
        if new_paid_total >= invoice_total_decimal:
            new_invoice_status = "paid"
        else:
            new_invoice_status = "partially_paid"

        invoice.status = new_invoice_status
        invoice.updated_at = now
        session.add(invoice)

        # 10. Tạo bản ghi thanh toán (Payment)
        payment_code = generate_payment_number(session, invoice)
        staff_display = current_user.full_name or current_user.email
        audit_note_content = (
            f"[Ghi nhận bởi: {staff_display}] {data.note.strip() if data.note else ''}"
        ).strip()

        payment = Payment(
            id=uuid.uuid4(),
            payment_number=payment_code,
            invoice_id=invoice.id,
            amount=float(amount_decimal),
            payment_method=normalized_method,
            payment_status="SUCCESS",
            transaction_reference=tx_code,
            paid_at=now,
            notes=audit_note_content,
            created_at=now,
        )
        session.add(payment)

        # 11. Ghi nhận nhật ký vào RepairStatusHistory cho đơn sửa chữa liên quan
        appointment = session.get(Appointment, invoice.appointment_id)
        if appointment:
            audit_msg = (
                f"Ghi nhận thanh toán {float(amount_decimal):,.0f} đ ({normalized_method}) "
                f"cho hóa đơn {invoice.invoice_number}. "
                f"Trạng thái hóa đơn: {new_invoice_status}. "
                f"Người ghi nhận: {staff_display}"
            )
            if tx_code:
                audit_msg += f". Mã GD: {tx_code}"

            history = RepairStatusHistory(
                appointment_id=appointment.id,
                previous_status=appointment.status,
                new_status=appointment.status,
                note=audit_msg,
                changed_by_user_id=current_user.id,
                created_at=now,
            )
            session.add(history)

        # 12. Ghi nhật ký hệ thống (SystemLog)
        system_log = SystemLog(
            action="RECORD_PAYMENT",
            entity_name="payment",
            entity_id=str(payment.id),
            details=(
                f"Hóa đơn: {invoice.invoice_number}, Số tiền: {float(amount_decimal):,.0f} đ, "
                f"Phương thức: {normalized_method}, Trạng thái sau TT: {new_invoice_status}"
            ),
            user_id=current_user.id,
            created_at=now,
        )
        session.add(system_log)

        # 13. Cam kết transaction an toàn
        session.commit()
        session.refresh(payment)
        session.refresh(invoice)

        logger.info(
            f"Ghi nhận thanh toán thành công: {payment.payment_number} ({payment.amount:,.0f} đ) "
            f"cho hóa đơn {invoice.invoice_number}. Trạng thái mới: {new_invoice_status}"
        )

        return _build_payment_detail(
            session=session,
            payment=payment,
            invoice=invoice,
            current_user=current_user,
        )

    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        logger.error(
            f"Lỗi không xác định khi ghi nhận thanh toán: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra lỗi trong quá trình ghi nhận thanh toán. Vui lòng thử lại sau.",
        ) from exc


def get_payment_by_id(
    session: Session,
    payment_id: uuid.UUID | str,
    current_user: User | None = None,
) -> PaymentDetail:
    """Lấy thông tin chi tiết của một giao dịch thanh toán."""
    _ = current_user
    payment: Payment | None = None
    if isinstance(payment_id, uuid.UUID):
        payment = session.get(Payment, payment_id)
    else:
        try:
            val_uuid = uuid.UUID(str(payment_id).strip())
            payment = session.get(Payment, val_uuid)
        except ValueError, TypeError, AttributeError:
            payment = session.exec(
                select(Payment).where(Payment.payment_number == str(payment_id).strip())
            ).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy giao dịch thanh toán với định danh: {payment_id}",
        )

    return _build_payment_detail(session, payment)


def get_invoice_payments(
    session: Session,
    invoice_id: uuid.UUID | str,
    current_user: User | None = None,
) -> list[PaymentDetail]:
    """Lấy danh sách các giao dịch thanh toán thuộc về một hóa đơn."""
    _ = current_user
    invoice = _resolve_invoice(session, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy hóa đơn với định danh: {invoice_id}",
        )

    payments = session.exec(
        select(Payment)
        .where(Payment.invoice_id == invoice.id)
        .order_by(col(Payment.paid_at).asc())
    ).all()

    return [_build_payment_detail(session, p, invoice) for p in payments]
