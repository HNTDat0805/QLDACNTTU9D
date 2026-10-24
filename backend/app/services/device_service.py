import uuid

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.logging import get_logger
from app.models import (
    Customer,
    Device,
    DevicePublic,
    DeviceUpdate,
    User,
    get_datetime_utc,
)

logger = get_logger("app.services.device_service")


def update_device(
    session: Session,
    device_id: uuid.UUID,
    device_in: DeviceUpdate,
    current_user: User,
) -> DevicePublic:
    """
    Cập nhật thông tin thiết bị đã tồn tại:
    - Kiểm tra thiết bị có tồn tại hay không (404 Not Found).
    - Phân quyền: Nhân viên cửa hàng hoặc Khách hàng sở hữu thiết bị (403 Forbidden nếu không có quyền).
    - Chỉ cập nhật những trường được gửi trong request (không ghi đè giá trị None khi không gửi).
    - Không cho phép thay đổi ID, customer_id hoặc các trường hệ thống ngoài phạm vi.
    - Cập nhật thời điểm updated_at và lưu nhất quán.
    """
    logger.info(
        f"Bắt đầu cập nhật thiết bị device_id={device_id} bởi user={current_user.id} ({current_user.email})"
    )

    device = session.get(Device, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy thiết bị với ID: {device_id}",
        )

    # Kiểm tra phân quyền: Nhân viên cửa hàng hoặc Khách hàng chủ sở hữu thiết bị
    is_staff_or_admin = current_user.is_superuser or (
        (current_user.role or "").lower() in ["admin", "manager", "staff", "technician"]
    )

    if not is_staff_or_admin:
        customer = session.get(Customer, device.customer_id)
        is_owner = False
        if customer:
            if customer.user_id and customer.user_id == current_user.id:
                is_owner = True
            elif (
                customer.email
                and customer.email.strip().lower() == current_user.email.strip().lower()
            ):
                is_owner = True

        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền cập nhật thông tin thiết bị của khách hàng khác",
            )

    update_dict = device_in.model_dump(exclude_unset=True)

    # Không cho phép thay đổi ID hoặc customer_id
    update_dict.pop("id", None)
    update_dict.pop("customer_id", None)
    update_dict.pop("created_at", None)

    for field, value in update_dict.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(device, field, value)

    device.updated_at = get_datetime_utc()
    session.add(device)
    session.commit()
    session.refresh(device)

    logger.info(
        f"Cập nhật thành công thiết bị {device.brand} {device.model} (ID: {device.id})"
    )
    return DevicePublic.model_validate(device)
