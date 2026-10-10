import uuid
from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    AppointmentBookingCreate,
    AppointmentBookingResponse,
    AppointmentBookingUpdate,
    AppointmentCancelRequest,
    AppointmentCancelResponse,
    AppointmentConfirmResponse,
)
from app.services import slot_service

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post(
    "",
    response_model=AppointmentBookingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_appointment(
    session: SessionDep,
    body: AppointmentBookingCreate,
) -> AppointmentBookingResponse:
    """API 2: Tạo mới lịch hẹn sửa chữa khi slot được chọn còn trống."""
    return slot_service.create_booking_appointment(session=session, data=body)


@router.patch(
    "/{appointment_id}",
    response_model=AppointmentBookingResponse,
)
def update_appointment(
    session: SessionDep,
    appointment_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch hẹn")],
    body: AppointmentBookingUpdate,
) -> AppointmentBookingResponse:
    """API 3: Cập nhật thông tin lịch hẹn (đổi ngày giờ hoặc kỹ thuật viên)."""
    return slot_service.update_booking_appointment(
        session=session, appointment_id=appointment_id, data=body
    )


@router.patch(
    "/{appointment_id}/confirm",
    response_model=AppointmentConfirmResponse,
    summary="Xác nhận lịch hẹn",
)
def confirm_appointment(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch hẹn")],
) -> AppointmentConfirmResponse:
    """API: Cho phép người dùng có quyền quản lý xác nhận một lịch hẹn hợp lệ."""
    return slot_service.confirm_appointment(
        session=session, appointment_id=appointment_id, current_user=current_user
    )


@router.patch(
    "/{appointment_id}/cancel",
    response_model=AppointmentCancelResponse,
    summary="Hủy lịch hẹn",
)
def cancel_appointment(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch hẹn")],
    body: AppointmentCancelRequest,
) -> AppointmentCancelResponse:
    """API: Cho phép người dùng có quyền hủy một lịch hẹn hợp lệ và ghi nhận lý do hủy."""
    return slot_service.cancel_appointment(
        session=session,
        appointment_id=appointment_id,
        data=body,
        current_user=current_user,
    )
