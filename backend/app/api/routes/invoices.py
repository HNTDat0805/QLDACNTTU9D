import uuid

from fastapi import APIRouter, Path, Query, status

from app.api.deps import RequireStaff, SessionDep
from app.models import (
    InvoiceCreateRequest,
    InvoiceResponse,
    InvoicesPublic,
)
from app.services import invoice_service

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo hóa đơn cho đơn sửa chữa (Task 315)",
    description="""
API tạo hóa đơn cho phiếu sửa chữa điện thoại:
- Hóa đơn liên kết trực tiếp với đơn sửa chữa (`repair_order_id`).
- Tự động lấy thông tin khách hàng từ đơn sửa chữa.
- Tự động lấy danh sách dịch vụ và các hạng mục sửa chữa đã được xác nhận (ưu tiên báo giá duyệt `ACCEPTED`, hoặc các dịch vụ đã tiếp nhận).
- Tự động tính toán tổng tiền hóa đơn ở backend dựa trên số lượng và đơn giá, chống gian lận dữ liệu từ phía client.
- Chặn tạo hóa đơn từ đơn sửa chữa không tồn tại (404 Not Found) hoặc đã bị hủy (400 Bad Request).
- Chặn tạo hóa đơn trùng lặp cho cùng một đơn sửa chữa (409 Conflict).
- Chặn tạo hóa đơn nếu đơn sửa chữa không có hạng mục nào hợp lệ (400 Bad Request).
- Khởi tạo trạng thái hóa đơn là `unpaid` (chưa thanh toán).
- Sử dụng database transaction an toàn, tự động rollback khi phát sinh lỗi.
- Quyền truy cập: Nhân viên hoặc quản lý cửa hàng (`RequireStaff`: Admin, Manager, Staff, Technician).
""",
)
def create_invoice(
    session: SessionDep,
    current_user: RequireStaff,
    body: InvoiceCreateRequest,
) -> InvoiceResponse:
    detail = invoice_service.create_invoice_for_repair_order(
        session=session,
        data=body,
        current_user=current_user,
    )
    return InvoiceResponse(
        success=True,
        message="Tạo hóa đơn thành công",
        data=detail,
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết hóa đơn",
    description="Lấy thông tin chi tiết hóa đơn cùng các hạng mục và lịch sử thanh toán liên quan.",
)
def get_invoice_detail(
    session: SessionDep,
    current_user: RequireStaff,
    invoice_id: str = Path(..., description="UUID hoặc mã số hóa đơn"),
) -> InvoiceResponse:
    detail = invoice_service.get_invoice_by_id(
        session=session,
        invoice_id=invoice_id,
        current_user=current_user,
    )
    return InvoiceResponse(
        success=True,
        message="Lấy thông tin hóa đơn thành công",
        data=detail,
    )


@router.get(
    "",
    response_model=InvoicesPublic,
    status_code=status.HTTP_200_OK,
    summary="Danh sách hóa đơn sửa chữa",
    description="Truy vấn danh sách hóa đơn theo phân trang và bộ lọc trạng thái.",
)
def list_invoices(
    session: SessionDep,
    _current_user: RequireStaff,
    skip: int = Query(0, ge=0, description="Vị trí bắt đầu"),
    limit: int = Query(20, ge=1, le=100, description="Số lượng bản ghi tối đa"),
    status: str | None = Query(
        None, description="Bộ lọc trạng thái (unpaid, partially_paid, paid, cancelled)"
    ),
    customer_id: uuid.UUID | None = Query(None, description="Lọc theo khách hàng"),
) -> InvoicesPublic:
    items, total = invoice_service.list_invoices(
        session=session,
        skip=skip,
        limit=limit,
        status_filter=status,
        customer_id=customer_id,
    )
    return InvoicesPublic(data=items, count=total)
