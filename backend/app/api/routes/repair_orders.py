import uuid

from fastapi import APIRouter, status

from app.api.deps import RequireStaff, SessionDep
from app.models import (
    AssignTechnicianRequest,
    AssignTechnicianResponse,
    RepairStatusUpdateRequest,
    RepairStatusUpdateResponse,
)
from app.services import repair_order_service

router = APIRouter(prefix="/repair-orders", tags=["repair-orders"])


@router.patch(
    "/{repair_order_id}/status",
    response_model=RepairStatusUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật trạng thái xử lý của phiếu sửa chữa",
    description="""
API cập nhật trạng thái xử lý của phiếu sửa chữa:
- Kiểm tra phiếu sửa chữa tồn tại.
- Kiểm tra chuyển trạng thái hợp lệ theo chu trình sửa chữa.
- Chặn cập nhật khi phiếu sửa chữa đã kết thúc (COMPLETED hoặc CANCELLED).
- Tự động cập nhật `actual_completion_date` khi hoàn tất hoặc `cancellation_reason` khi hủy.
- Ghi nhận lịch sử thay đổi vào `repair_status_history` trong cùng một transaction.
- Quyền truy cập: Nhân viên cửa hàng (`RequireStaff`: Admin, Manager, Staff, Technician).
""",
)
def update_repair_status(
    session: SessionDep,
    current_user: RequireStaff,
    repair_order_id: uuid.UUID,
    body: RepairStatusUpdateRequest,
) -> RepairStatusUpdateResponse:
    data = repair_order_service.update_repair_status(
        session=session,
        repair_order_id=repair_order_id,
        data=body,
        current_user=current_user,
    )
    return RepairStatusUpdateResponse(
        success=True,
        message=f"Cập nhật trạng thái phiếu sửa chữa sang {data.current_status} thành công",
        data=data,
    )


@router.patch(
    "/{repair_order_id}/technician",
    response_model=AssignTechnicianResponse,
    status_code=status.HTTP_200_OK,
    summary="Phân công kỹ thuật viên phụ trách phiếu sửa chữa",
    description="""
API phân công hoặc thay đổi kỹ thuật viên cho phiếu sửa chữa:
- Kiểm tra phiếu sửa chữa tồn tại và chưa kết thúc.
- Kiểm tra kỹ thuật viên tồn tại, đang hoạt động (`is_active=True`) và không đăng ký nghỉ (`OFF`) trong ngày.
- Ghi nhận lịch sử phân công vào `repair_status_history` trong cùng một transaction.
- Quyền truy cập: Nhân viên cửa hàng (`RequireStaff`: Admin, Manager, Staff, Technician).
""",
)
def assign_technician(
    session: SessionDep,
    current_user: RequireStaff,
    repair_order_id: uuid.UUID,
    body: AssignTechnicianRequest,
) -> AssignTechnicianResponse:
    data = repair_order_service.assign_technician_to_repair(
        session=session,
        repair_order_id=repair_order_id,
        data=body,
        current_user=current_user,
    )
    return AssignTechnicianResponse(
        success=True,
        message=f"Phân công kỹ thuật viên {data.technician_name} cho phiếu sửa chữa thành công",
        data=data,
    )
