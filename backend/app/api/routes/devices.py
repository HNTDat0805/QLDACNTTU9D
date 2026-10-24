import uuid

from fastapi import APIRouter, Path, status

from app.api.deps import CurrentUser, SessionDep
from app.models import DeviceResponse, DeviceUpdate
from app.services import device_service

router = APIRouter(prefix="/devices", tags=["devices"])


@router.patch(
    "/{device_id}",
    response_model=DeviceResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật thông tin thiết bị sửa chữa",
    description="""
API cập nhật thông tin thiết bị sửa chữa:
- Kiểm tra thiết bị có tồn tại hay không.
- Phân quyền: Nhân viên cửa hàng hoặc Khách hàng sở hữu thiết bị.
- Chỉ cập nhật những trường nghiệp vụ được gửi trong request (không ghi đè các trường không gửi).
- Không cho phép sửa đổi ID, customer_id hoặc các trường hệ thống ngoài phạm vi.
- Trả về dữ liệu thiết bị sau khi cập nhật thành công.
""",
)
def update_device(
    session: SessionDep,
    current_user: CurrentUser,
    device_id: uuid.UUID = Path(..., description="ID của thiết bị cần cập nhật"),
    body: DeviceUpdate = DeviceUpdate(),
) -> DeviceResponse:
    device = device_service.update_device(
        session=session,
        device_id=device_id,
        device_in=body,
        current_user=current_user,
    )
    return DeviceResponse(
        success=True,
        message=f"Cập nhật thông tin thiết bị {device.brand} {device.model} thành công",
        data=device,
    )
