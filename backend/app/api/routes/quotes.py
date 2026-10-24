from fastapi import APIRouter, status

from app.api.deps import RequireStaff, SessionDep
from app.models import QuotationCreate, QuotationResponse
from app.services import quote_service

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post(
    "",
    response_model=QuotationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo báo giá sửa chữa mới",
    description="""
API tạo báo giá sửa chữa cho một phiếu sửa chữa (Appointment):
- Nhận định danh phiếu sửa chữa qua `appointment_id` hoặc `appointment_number`.
- Nhận danh sách các hạng mục báo giá (dịch vụ có sẵn hoặc hạng mục tùy biến linh kiện/công thợ).
- Xác minh phiếu sửa chữa đang ở trạng thái hợp lệ để báo giá (chưa bị hủy hoặc đã hoàn thành).
- Tự động tính toán thành tiền từng hạng mục và tổng tiền ở backend (tránh sai số số thực).
- Khởi tạo trạng thái báo giá (mặc định là `DRAFT`).
- Gắn mã báo giá duy nhất (ví dụ: `QUO-YYYYMMDD-XXXX`).
- Lưu trữ an toàn bằng transaction.
- Quyền truy cập: Nhân viên cửa hàng (`RequireStaff`: Admin, Manager, Staff, Technician).
""",
)
def create_quotation(
    session: SessionDep,
    current_user: RequireStaff,
    body: QuotationCreate,
) -> QuotationResponse:
    detail = quote_service.create_repair_quotation(
        session=session,
        quote_in=body,
        current_user=current_user,
    )
    return QuotationResponse(
        success=True,
        message=f"Tạo báo giá sửa chữa {detail.quote_number} thành công",
        data=detail,
    )
