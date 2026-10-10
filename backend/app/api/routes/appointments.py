import uuid
from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import SessionDep
from app.models import (
    AppointmentBookingCreate,
    AppointmentBookingResponse,
    AppointmentBookingUpdate,
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
