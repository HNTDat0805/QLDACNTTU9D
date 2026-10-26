import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import RequireManager, RequireStaff, SessionDep
from app.models import (
    Message,
    TechnicianScheduleCreate,
    TechnicianSchedulePublic,
    TechnicianSchedulesPublic,
    TechnicianScheduleStatusUpdate,
    TechnicianScheduleUpdate,
)
from app.services import schedule_service

router = APIRouter(prefix="/work-schedules", tags=["work-schedules"])


@router.get(
    "",
    response_model=TechnicianSchedulesPublic,
    summary="Lấy danh sách ca làm việc",
)
def read_work_schedules(
    session: SessionDep,
    _: RequireStaff,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    technician_id: uuid.UUID | None = Query(
        default=None, description="Lọc theo kỹ thuật viên"
    ),
    work_date: date | None = Query(default=None, description="Lọc theo ngày cụ thể"),
    start_date: date | None = Query(default=None, description="Lọc từ ngày"),
    end_date: date | None = Query(default=None, description="Lọc đến ngày"),
    status: str | None = Query(
        default=None, description="Lọc theo trạng thái ca: AVAILABLE, BUSY, OFF"
    ),
) -> TechnicianSchedulesPublic:
    """API: Lấy lịch làm việc của các kỹ thuật viên theo ngày hoặc khoảng thời gian."""
    return schedule_service.get_work_schedules(
        session=session,
        skip=skip,
        limit=limit,
        technician_id=technician_id,
        work_date=work_date,
        start_date=start_date,
        end_date=end_date,
        status_filter=status,
    )


@router.post(
    "",
    response_model=TechnicianSchedulePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo ca làm việc mới",
)
def create_work_schedule(
    session: SessionDep,
    _: RequireStaff,
    body: TechnicianScheduleCreate,
) -> TechnicianSchedulePublic:
    """API: Tạo lịch làm việc mới với kiểm tra thời gian hợp lệ và chống trùng lặp ca."""
    return schedule_service.create_work_schedule(session=session, data=body)


@router.get(
    "/{schedule_id}",
    response_model=TechnicianSchedulePublic,
    summary="Xem chi tiết ca làm việc",
)
def read_work_schedule_by_id(
    session: SessionDep,
    _: RequireStaff,
    schedule_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch làm việc")],
) -> TechnicianSchedulePublic:
    """API: Xem chi tiết một lịch làm việc."""
    return schedule_service.get_work_schedule_by_id(
        session=session, schedule_id=schedule_id
    )


@router.patch(
    "/{schedule_id}",
    response_model=TechnicianSchedulePublic,
    summary="Cập nhật ca làm việc",
)
def update_work_schedule(
    session: SessionDep,
    _: RequireStaff,
    schedule_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch làm việc")],
    body: TechnicianScheduleUpdate,
) -> TechnicianSchedulePublic:
    """API: Cập nhật lịch làm việc với kiểm tra xung đột trùng ca và lịch hẹn hiện hữu."""
    return schedule_service.update_work_schedule(
        session=session, schedule_id=schedule_id, data=body
    )


@router.patch(
    "/{schedule_id}/status",
    response_model=TechnicianSchedulePublic,
    summary="Cập nhật trạng thái ca làm việc",
)
def update_work_schedule_status(
    session: SessionDep,
    _: RequireStaff,
    schedule_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch làm việc")],
    body: TechnicianScheduleStatusUpdate,
) -> TechnicianSchedulePublic:
    """API: Cập nhật trạng thái ca làm việc (AVAILABLE, BUSY, OFF) với kiểm tra an toàn lịch hẹn."""
    return schedule_service.update_work_schedule_status(
        session=session,
        schedule_id=schedule_id,
        status_val=body.status,
        notes=body.notes,
    )


@router.delete(
    "/{schedule_id}",
    response_model=Message,
    summary="Xóa ca làm việc",
)
def delete_work_schedule(
    session: SessionDep,
    _: RequireManager,
    schedule_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch làm việc")],
) -> Message:
    """API: Xóa lịch làm việc khi không có lịch hẹn phân công trong khoảng thời gian này."""
    return schedule_service.delete_work_schedule(
        session=session, schedule_id=schedule_id
    )
