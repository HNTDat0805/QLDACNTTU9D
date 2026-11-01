import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import SQLModel, col, select

from app.api.deps import SessionDep
from app.models import (
    AvailableSlotsResponse,
    Service,
    SlotCheckRequest,
    SlotCheckResponse,
    Technician,
    TechnicianSchedule,
)
from app.services import slot_service

router = APIRouter(prefix="/slots", tags=["slots"])


class BookingTechnician(SQLModel):
    id: uuid.UUID
    full_name: str
    specialization: str | None = None


@router.get("/technicians", response_model=list[BookingTechnician])
def read_booking_technicians(
    session: SessionDep, service_id: uuid.UUID, slot_date: date
) -> list[BookingTechnician]:
    """Public booking choices: no phone, account ID or internal personnel fields."""
    service = session.get(Service, service_id)
    if not service or not service.is_active:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy dịch vụ đang hoạt động"
        )
    rows = session.exec(
        select(Technician)
        .join(TechnicianSchedule)
        .where(
            col(Technician.is_active).is_(True),
            TechnicianSchedule.work_date == slot_date,
            TechnicianSchedule.status == "AVAILABLE",
        )
        .distinct()
    ).all()
    return [
        BookingTechnician(
            id=t.id, full_name=t.full_name, specialization=t.specialization
        )
        for t in rows
    ]


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
