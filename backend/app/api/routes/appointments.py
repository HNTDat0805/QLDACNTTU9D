import uuid
from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import CurrentUser, CurrentUserOptional, SessionDep
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
bookings_router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post(
    "",
    response_model=AppointmentBookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo đặt chỗ mới",
)
def create_appointment(
    session: SessionDep,
    body: AppointmentBookingCreate,
) -> AppointmentBookingResponse:
    """API 1: Tạo mới lịch đặt chỗ sửa chữa khi slot được chọn còn trống."""
    return slot_service.create_booking_appointment(session=session, data=body)


@router.patch(
    "/{appointment_id}",
    response_model=AppointmentBookingResponse,
    summary="Cập nhật đặt chỗ",
)
def update_appointment(
    session: SessionDep,
    appointment_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch hẹn")],
    body: AppointmentBookingUpdate,
    current_user: CurrentUserOptional = None,
) -> AppointmentBookingResponse:
    """API 2: Cập nhật thông tin đặt chỗ (đổi ngày giờ, kỹ thuật viên, liên hệ hoặc ghi chú)."""
    return slot_service.update_booking_appointment(
        session=session,
        appointment_id=appointment_id,
        data=body,
        current_user=current_user,
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
    summary="Hủy đặt chỗ",
)
def cancel_appointment(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch hẹn")],
    body: AppointmentCancelRequest,
) -> AppointmentCancelResponse:
    """API 3: Cho phép người dùng có quyền hủy đặt chỗ và ghi nhận lý do hủy."""
    return slot_service.cancel_appointment(
        session=session,
        appointment_id=appointment_id,
        data=body,
        current_user=current_user,
    )


# Register identical endpoints under bookings_router
bookings_router.add_api_route(
    "",
    create_appointment,
    methods=["POST"],
    response_model=AppointmentBookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo đặt chỗ mới",
)
bookings_router.add_api_route(
    "/{appointment_id}",
    update_appointment,
    methods=["PATCH"],
    response_model=AppointmentBookingResponse,
    summary="Cập nhật đặt chỗ",
)
bookings_router.add_api_route(
    "/{appointment_id}/cancel",
    cancel_appointment,
    methods=["PATCH"],
    response_model=AppointmentCancelResponse,
    summary="Hủy đặt chỗ",
)
bookings_router.add_api_route(
    "/{appointment_id}/confirm",
    confirm_appointment,
    methods=["PATCH"],
    response_model=AppointmentConfirmResponse,
    summary="Xác nhận đặt chỗ",
)
