import uuid

from fastapi import APIRouter, Query, status
from sqlmodel import col, func, select

from app.api.deps import RequireStaff, SessionDep
from app.models import (
    Appointment,
    AppointmentHistoryDetail,
    AppointmentsHistoryPublic,
    AssignTechnicianRequest,
    AssignTechnicianResponse,
    RepairStatusUpdateRequest,
    RepairStatusUpdateResponse,
)
from app.services import access_service, history_service, repair_order_service

router = APIRouter(prefix="/repair-orders", tags=["repair-orders"])


@router.get("", response_model=AppointmentsHistoryPublic)
def read_repair_orders(
    session: SessionDep,
    current_user: RequireStaff,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = None,
) -> AppointmentsHistoryPublic:
    ids = access_service.accessible_appointment_ids(session, current_user)
    query = select(Appointment)
    count = select(func.count()).select_from(Appointment)
    if ids is not None:
        query = query.where(col(Appointment.id).in_(ids))
        count = count.where(col(Appointment.id).in_(ids))
    if status_filter:
        query = query.where(Appointment.status == status_filter)
        count = count.where(Appointment.status == status_filter)
    rows = session.exec(
        query.order_by(col(Appointment.appointment_date).desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return AppointmentsHistoryPublic(
        data=[
            history_service.build_appointment_history_detail(session, row)
            for row in rows
        ],
        count=session.exec(count).one(),
    )


@router.get("/{repair_order_id}", response_model=AppointmentHistoryDetail)
def read_repair_order(
    session: SessionDep, current_user: RequireStaff, repair_order_id: uuid.UUID
) -> AppointmentHistoryDetail:
    return history_service.get_appointment_detail(
        session, repair_order_id, current_user
    )


@router.patch(
    "/{repair_order_id}/status",
    response_model=RepairStatusUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật trạng thái xử lý của phiếu sửa chữa",
    description="""
API cập nhật trạng thái xử lý của phiếu sửa chữa:
- Kiểm tra phiếu sửa chữa tồn tại.
- Kiểm tra chuyển trạng thái hợp lệ theo chu trình sửa chữa.
- Chặn cập nhật khi phiếu sửa chữa đã kết thúc (COMPLETED hoặc CANCELLED).
- Tự động cập nhật `actual_completion_date` khi hoàn tất hoặc `cancellation_reason` khi hủy.
- Ghi nhận lịch sử thay đổi vào `repair_status_history` trong cùng một transaction.
- Quyền truy cập: Nhân viên cửa hàng (`RequireStaff`: Admin, Manager, Staff, Technician).
""",
)
def update_repair_status(
    session: SessionDep,
    current_user: RequireStaff,
    repair_order_id: uuid.UUID,
    body: RepairStatusUpdateRequest,
) -> RepairStatusUpdateResponse:
    data = repair_order_service.update_repair_status(
        session=session,
        repair_order_id=repair_order_id,
        data=body,
        current_user=current_user,
    )
    return RepairStatusUpdateResponse(
        success=True,
        message=f"Cập nhật trạng thái phiếu sửa chữa sang {data.current_status} thành công",
        data=data,
    )


@router.patch(
    "/{repair_order_id}/technician",
    response_model=AssignTechnicianResponse,
    status_code=status.HTTP_200_OK,
    summary="Phân công kỹ thuật viên phụ trách phiếu sửa chữa",
    description="""
API phân công hoặc thay đổi kỹ thuật viên cho phiếu sửa chữa:
- Kiểm tra phiếu sửa chữa tồn tại và chưa kết thúc.
- Kiểm tra kỹ thuật viên tồn tại, đang hoạt động (`is_active=True`) và không đăng ký nghỉ (`OFF`) trong ngày.
- Ghi nhận lịch sử phân công vào `repair_status_history` trong cùng một transaction.
- Quyền truy cập: Nhân viên cửa hàng (`RequireStaff`: Admin, Manager, Staff, Technician).
""",
)
def assign_technician(
    session: SessionDep,
    current_user: RequireStaff,
    repair_order_id: uuid.UUID,
    body: AssignTechnicianRequest,
) -> AssignTechnicianResponse:
    data = repair_order_service.assign_technician_to_repair(
        session=session,
        repair_order_id=repair_order_id,
        data=body,
        current_user=current_user,
    )
    return AssignTechnicianResponse(
        success=True,
        message=f"Phân công kỹ thuật viên {data.technician_name} cho phiếu sửa chữa thành công",
        data=data,
    )
