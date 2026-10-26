import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CurrentUser, RequireStaff, SessionDep
from app.models import (
    AppointmentBookingCreate,
    AppointmentBookingResponse,
    QueueItemPublic,
    QueueListResponse,
    QueueStatusUpdate,
)
from app.services import queue_service

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get(
    "",
    response_model=QueueListResponse,
    summary="Lấy danh sách hàng chờ sửa chữa",
)
def read_queue(
    session: SessionDep,
    _: RequireStaff,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    date: date | None = Query(default=None, description="Lọc hàng chờ theo ngày"),
    status: str | None = Query(
        default=None,
        description="Lọc theo trạng thái trong hàng chờ (mặc định lấy PENDING, CONFIRMED, IN_PROGRESS)",
    ),
    technician_id: uuid.UUID | None = Query(
        default=None, description="Lọc theo kỹ thuật viên"
    ),
) -> QueueListResponse:
    """API: Lấy danh sách lịch hẹn trong hàng chờ theo thứ tự ưu tiên xử lý (thời gian hẹn và thời điểm tạo tăng dần)."""
    return queue_service.get_queue_list(
        session=session,
        skip=skip,
        limit=limit,
        queue_date=date,
        status_filter=status,
        technician_id=technician_id,
    )


@router.post(
    "",
    response_model=AppointmentBookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm lịch hẹn vào hàng chờ tiếp nhận",
)
def add_appointment_to_queue(
    session: SessionDep,
    _: RequireStaff,
    body: AppointmentBookingCreate,
) -> AppointmentBookingResponse:
    """API: Thêm lịch hẹn vào hàng chờ tiếp nhận cho khách vãng lai hoặc đặt hẹn nhanh."""
    return queue_service.add_to_queue(session=session, data=body)


@router.get(
    "/{appointment_id}",
    response_model=QueueItemPublic,
    summary="Xem chi tiết mục trong hàng chờ",
)
def read_queue_item(
    session: SessionDep,
    _: RequireStaff,
    appointment_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch hẹn")],
) -> QueueItemPublic:
    """API: Xem chi tiết một mục trong hàng chờ và vị trí thứ tự hiện tại của nó."""
    return queue_service.get_queue_item(session=session, appointment_id=appointment_id)


@router.patch(
    "/{appointment_id}/status",
    response_model=QueueItemPublic,
    summary="Cập nhật trạng thái tiếp nhận và xử lý trong hàng chờ",
)
def update_queue_status(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch hẹn")],
    body: QueueStatusUpdate,
) -> QueueItemPublic:
    """API: Cập nhật trạng thái xử lý hàng chờ (CONFIRMED, IN_PROGRESS, COMPLETED, CANCELLED) và ghi nhận nhật ký lịch sử."""
    return queue_service.update_queue_status(
        session=session,
        appointment_id=appointment_id,
        data=body,
        current_user=current_user,
    )
