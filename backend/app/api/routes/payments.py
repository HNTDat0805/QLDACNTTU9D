from fastapi import APIRouter, Path, status

from app.api.deps import RequireStaff, SessionDep
from app.models import (
    PaymentCreateRequest,
    PaymentResponse,
    PaymentsPublic,
)
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ghi nhận thanh toán cho hóa đơn (Task 319)",
    description="""
API ghi nhận giao dịch thanh toán của khách hàng cho hóa đơn:
- Hỗ trợ các phương thức thanh toán theo thiết kế FixPhone:
  + Tiền mặt tại cửa hàng (`cash`).
  + Thanh toán khi nhận máy (`cod`).
  + Chuyển khoản / QR (`bank_transfer`).
  + Thẻ ATM / Visa / Mastercard (`card`).
  + Ví điện tử (`e_wallet`).
- Kiểm tra tính hợp lệ của hóa đơn:
  + Hóa đơn tồn tại (404 Not Found).
  + Hóa đơn không bị hủy (400 Bad Request).
  + Hóa đơn chưa thanh toán đủ (400 Bad Request).
- Kiểm tra số tiền thanh toán:
  + Số tiền thanh toán phải > 0.
  + Không được vượt quá số tiền còn nợ của hóa đơn.
- Hỗ trợ thanh toán nhiều lần: Tự động cập nhật trạng thái hóa đơn (`partially_paid` hoặc `paid`).
- Chống thanh toán trùng lặp (Anti Duplicate Payment):
  + Chặn trùng mã giao dịch (`transaction_code`) với mã lỗi 409 Conflict.
  + Chặn gửi lặp lại giao dịch tương tự trong vòng 60 giây với mã lỗi 409 Conflict.
- Xác thực giao dịch phi tiền mặt: Đối với chuyển khoản, QR, thẻ, ví điện tử, yêu cầu cung cấp mã giao dịch hoặc ghi chú xác minh từ nhân viên.
- Thực hiện giao dịch và cập nhật trạng thái trong cùng một database transaction. Tự động rollback khi phát sinh lỗi.
- Quyền truy cập: Nhân viên hoặc quản lý cửa hàng (`RequireStaff`: Admin, Manager, Staff, Technician).
""",
)
def record_payment(
    session: SessionDep,
    current_user: RequireStaff,
    body: PaymentCreateRequest,
) -> PaymentResponse:
    detail = payment_service.record_payment(
        session=session,
        data=body,
        current_user=current_user,
    )
    return PaymentResponse(
        success=True,
        message="Ghi nhận thanh toán thành công",
        data=detail,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết giao dịch thanh toán",
    description="Tra cứu thông tin chi tiết một giao dịch thanh toán đã ghi nhận.",
)
def get_payment_detail(
    session: SessionDep,
    current_user: RequireStaff,
    payment_id: str = Path(..., description="UUID hoặc mã thanh toán (PAY-...)"),
) -> PaymentResponse:
    detail = payment_service.get_payment_by_id(
        session=session,
        payment_id=payment_id,
        current_user=current_user,
    )
    return PaymentResponse(
        success=True,
        message="Lấy thông tin thanh toán thành công",
        data=detail,
    )


@router.get(
    "/by-invoice/{invoice_id}",
    response_model=PaymentsPublic,
    status_code=status.HTTP_200_OK,
    summary="Danh sách thanh toán theo hóa đơn",
    description="Lấy toàn bộ lịch sử các giao dịch thanh toán của một hóa đơn cụ thể.",
)
def get_invoice_payments(
    session: SessionDep,
    current_user: RequireStaff,
    invoice_id: str = Path(..., description="UUID hoặc mã hóa đơn"),
) -> PaymentsPublic:
    payments = payment_service.get_invoice_payments(
        session=session,
        invoice_id=invoice_id,
        current_user=current_user,
    )
    return PaymentsPublic(data=payments, count=len(payments))
