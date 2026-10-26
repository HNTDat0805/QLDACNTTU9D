import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import RequireAdmin, RequireManager, RequireStaff, SessionDep
from app.models import (
    Message,
    TechnicianCreate,
    TechnicianPublic,
    TechniciansPublic,
    TechnicianStatusUpdate,
    TechnicianUpdate,
)
from app.services import technician_service

router = APIRouter(prefix="/technicians", tags=["technicians"])


@router.get(
    "",
    response_model=TechniciansPublic,
    summary="Lấy danh sách kỹ thuật viên",
)
def read_technicians(
    session: SessionDep,
    _: RequireStaff,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    is_active: bool | None = Query(
        default=None, description="Lọc theo trạng thái hoạt động"
    ),
    specialization: str | None = Query(default=None, description="Lọc theo chuyên môn"),
    q: str | None = Query(
        default=None, description="Tìm kiếm theo tên, số điện thoại hoặc chuyên môn"
    ),
) -> TechniciansPublic:
    """API: Lấy danh sách kỹ thuật viên có phân trang, lọc theo trạng thái, chuyên môn và tìm kiếm."""
    return technician_service.get_technicians(
        session=session,
        skip=skip,
        limit=limit,
        is_active=is_active,
        specialization=specialization,
        q=q,
    )


@router.post(
    "",
    response_model=TechnicianPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo kỹ thuật viên mới",
)
def create_technician(
    session: SessionDep,
    _: RequireManager,
    body: TechnicianCreate,
) -> TechnicianPublic:
    """API: Tạo kỹ thuật viên mới với kiểm tra số điện thoại duy nhất."""
    return technician_service.create_technician(session=session, data=body)


@router.get(
    "/{technician_id}",
    response_model=TechnicianPublic,
    summary="Xem chi tiết kỹ thuật viên",
)
def read_technician_by_id(
    session: SessionDep,
    _: RequireStaff,
    technician_id: Annotated[uuid.UUID, Path(description="Mã ID của kỹ thuật viên")],
) -> TechnicianPublic:
    """API: Xem thông tin chi tiết một kỹ thuật viên."""
    return technician_service.get_technician_by_id(
        session=session, technician_id=technician_id
    )


@router.patch(
    "/{technician_id}",
    response_model=TechnicianPublic,
    summary="Cập nhật thông tin kỹ thuật viên",
)
def update_technician(
    session: SessionDep,
    _: RequireManager,
    technician_id: Annotated[uuid.UUID, Path(description="Mã ID của kỹ thuật viên")],
    body: TechnicianUpdate,
) -> TechnicianPublic:
    """API: Cập nhật thông tin kỹ thuật viên."""
    return technician_service.update_technician(
        session=session, technician_id=technician_id, data=body
    )


@router.patch(
    "/{technician_id}/status",
    response_model=TechnicianPublic,
    summary="Cập nhật trạng thái hoạt động của kỹ thuật viên",
)
def update_technician_status(
    session: SessionDep,
    _: RequireManager,
    technician_id: Annotated[uuid.UUID, Path(description="Mã ID của kỹ thuật viên")],
    body: TechnicianStatusUpdate,
) -> TechnicianPublic:
    """API: Cập nhật trạng thái hoạt động hoặc tạm nghỉ (is_active: true/false) của kỹ thuật viên."""
    return technician_service.update_technician_status(
        session=session, technician_id=technician_id, is_active=body.is_active
    )


@router.delete(
    "/{technician_id}",
    response_model=Message,
    summary="Xóa kỹ thuật viên",
)
def delete_technician(
    session: SessionDep,
    _: RequireAdmin,
    technician_id: Annotated[uuid.UUID, Path(description="Mã ID của kỹ thuật viên")],
) -> Message:
    """API: Xóa kỹ thuật viên chỉ khi chưa có liên kết với lịch hẹn hoặc lịch làm việc."""
    return technician_service.delete_technician(
        session=session, technician_id=technician_id
    )
