from fastapi import APIRouter, status

from app.api.deps import RequireStaff, SessionDep
from app.models import DeviceIntakeCreate, DeviceIntakeResponse
from app.services import intake_service

router = APIRouter(prefix="/intake", tags=["intake"])


@router.post(
    "",
    response_model=DeviceIntakeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo phiếu tiếp nhận thiết bị sửa chữa",
    description="""
API tạo phiếu tiếp nhận thiết bị sửa chữa:
- Hỗ trợ tiếp nhận theo lịch hẹn có sẵn (`appointment_id`) hoặc tiếp nhận trực tiếp khách vãng lai (walk-in).
- Ghi nhận thông tin thiết bị, tình trạng ngoại quan (`physical_condition`), mô tả lỗi (`fault_description`), và phụ kiện bàn giao (`accessories_received`).
- Tự động sinh mã phiếu tiếp nhận (APPT-YYYYMMDD-XXXX).
- Khởi tạo trạng thái phiếu theo quy định (`CONFIRMED` hoặc `IN_PROGRESS`).
- Tự động ghi nhật ký kiểm toán vào `repair_status_history`.
- Quyền truy cập: Nhân viên cửa hàng (`RequireStaff`: Admin, Manager, Staff, Technician).
""",
)
def create_device_intake(
    session: SessionDep,
    current_user: RequireStaff,
    body: DeviceIntakeCreate,
) -> DeviceIntakeResponse:
    detail = intake_service.create_device_intake(
        session=session,
        intake_in=body,
        current_user=current_user,
    )
    return DeviceIntakeResponse(
        success=True,
        message=f"Tạo phiếu tiếp nhận thiết bị thành công (Mã phiếu: {detail.appointment_number})",
        data=detail,
    )
