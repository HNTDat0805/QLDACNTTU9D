import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import SessionDep
from app.models import AvailableSlotsResponse, SlotCheckRequest, SlotCheckResponse
from app.services import slot_service

router = APIRouter(prefix="/slots", tags=["slots"])


@router.get("/available", response_model=AvailableSlotsResponse)
def get_available_slots(
    session: SessionDep,
    date: Annotated[date, Query(description="Ngày cần kiểm tra (YYYY-MM-DD)")],
    service_id: Annotated[uuid.UUID, Query(description="Mã dịch vụ sửa chữa")],
    technician_id: Annotated[
        uuid.UUID | None, Query(description="Mã kỹ thuật viên (tùy chọn)")
    ] = None,
    slot_duration: Annotated[
        int | None,
        Query(
            ge=5,
            le=480,
            description="Thời lượng slot tùy chọn tính bằng phút",
        ),
    ] = None,
) -> AvailableSlotsResponse:
    """API 1: Lấy danh sách khung giờ (slot) còn trống theo ngày, dịch vụ và kỹ thuật viên."""
    return slot_service.get_available_slots(
        session=session,
        slot_date=date,
        service_id=service_id,
        technician_id=technician_id,
        slot_duration=slot_duration,
    )


@router.post("/check", response_model=SlotCheckResponse)
def check_slot(
    session: SessionDep,
    body: SlotCheckRequest,
) -> SlotCheckResponse:
    """API 4: Kiểm tra khả năng đặt một khung giờ (slot) cụ thể."""
    return slot_service.check_slot_availability(session=session, data=body)
