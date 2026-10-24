import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CurrentUser, CurrentUserOptional, RequireStaff, SessionDep
from app.models import (
    AppointmentAssignTechnicianRequest,
    AppointmentAssignTechnicianResponse,
    AppointmentBookingCreate,
    AppointmentBookingResponse,
    AppointmentBookingUpdate,
    AppointmentCancelRequest,
    AppointmentCancelResponse,
    AppointmentConfirmResponse,
    AppointmentHistoryDetail,
    AppointmentsHistoryPublic,
)
from app.services import history_service, slot_service

router = APIRouter(prefix="/appointments", tags=["appointments"])
bookings_router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get(
    "/history",
    response_model=AppointmentsHistoryPublic,
    summary="Tra cứu và lọc lịch sử lịch hẹn sửa chữa",
)
def read_appointments_history(
    session: SessionDep,
    _: RequireStaff,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    customer_id: uuid.UUID | None = Query(
        default=None, description="Lọc theo khách hàng"
    ),
    technician_id: uuid.UUID | None = Query(
        default=None, description="Lọc theo kỹ thuật viên"
    ),
    status: str | None = Query(
        default=None,
        description="Lọc theo trạng thái (có thể phân tách bằng dấu phẩy, ví dụ: COMPLETED,CANCELLED)",
    ),
    start_date: date | None = Query(default=None, description="Lọc từ ngày hẹn"),
    end_date: date | None = Query(default=None, description="Lọc đến ngày hẹn"),
    q: str | None = Query(
        default=None,
        description="Tìm kiếm theo mã lịch hẹn, số điện thoại hoặc tên khách hàng",
    ),
) -> AppointmentsHistoryPublic:
    """API: Tra cứu và lọc lịch sử lịch hẹn và sửa chữa toàn hệ thống."""
    return history_service.get_appointment_history_list(
        session=session,
        skip=skip,
        limit=limit,
        customer_id=customer_id,
        technician_id=technician_id,
        status_filter=status,
        start_date=start_date,
        end_date=end_date,
        q=q,
    )


@router.get(
    "/history/lookup",
    response_model=list[AppointmentHistoryDetail],
    summary="Tra cứu tiến độ lịch hẹn theo mã hoặc số điện thoại",
)
def lookup_appointment(
    session: SessionDep,
    current_user: CurrentUserOptional = None,
    appointment_number: str | None = Query(
        default=None, description="Mã lịch hẹn (ví dụ: APPT-20261015-A1B2)"
    ),
    phone_number: str | None = Query(
        default=None, description="Số điện thoại khách hàng"
    ),
) -> list[AppointmentHistoryDetail]:
    """API: Tra cứu nhanh lịch hẹn sửa chữa theo mã đặt chỗ hoặc số điện thoại."""
    return history_service.lookup_appointments(
        session=session,
        appointment_number=appointment_number,
        phone_number=phone_number,
        current_user=current_user,
    )


@router.get(
    "/{appointment_id}/detail",
    response_model=AppointmentHistoryDetail,
    summary="Xem chi tiết lịch hẹn kèm lịch sử trạng thái",
)
def read_appointment_detail(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch hẹn")],
) -> AppointmentHistoryDetail:
    """API: Xem chi tiết toàn diện của một lịch hẹn gồm thông tin khách hàng, thiết bị, dịch vụ và nhật ký trạng thái."""
    return history_service.get_appointment_detail(
        session=session, appointment_id=appointment_id, current_user=current_user
    )


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


@router.post(
    "/{appointment_id}/assign-technician",
    response_model=AppointmentAssignTechnicianResponse,
    status_code=status.HTTP_200_OK,
    summary="Phân công kỹ thuật viên cho lịch hẹn sửa chữa",
    description="""
API phân công một kỹ thuật viên vào lịch hẹn sửa chữa điện thoại:
- Kiểm tra dữ liệu đầu vào và quyền truy cập (yêu cầu nhân viên cửa hàng `RequireStaff`).
- Kiểm tra lịch hẹn tồn tại và chưa kết thúc (không ở trạng thái COMPLETED hoặc CANCELLED).
- Kiểm tra kỹ thuật viên tồn tại, đang hoạt động (`is_active=True`) và không đăng ký nghỉ phép (`OFF`).
- Kiểm tra kỹ thuật viên có chuyên môn phù hợp với các dịch vụ đã đăng ký trong lịch hẹn.
- Kiểm tra ca làm việc và xung đột trùng giờ với các lịch hẹn khác của kỹ thuật viên.
- Khóa dòng dữ liệu (`with_for_update`) chống xung đột tranh chấp đồng thời.
- Cập nhật phân công và tự động ghi nhật ký vào `repair_status_history` trong cùng transaction an toàn.
""",
)
def assign_technician_to_appointment(
    session: SessionDep,
    current_user: RequireStaff,
    appointment_id: Annotated[uuid.UUID, Path(description="Mã ID của lịch hẹn")],
    body: AppointmentAssignTechnicianRequest,
) -> AppointmentAssignTechnicianResponse:
    """API: Phân công kỹ thuật viên cho lịch hẹn sửa chữa."""
    return slot_service.assign_technician_to_appointment(
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
bookings_router.add_api_route(
    "/{appointment_id}/assign-technician",
    assign_technician_to_appointment,
    methods=["POST"],
    response_model=AppointmentAssignTechnicianResponse,
    status_code=status.HTTP_200_OK,
    summary="Phân công kỹ thuật viên cho lịch hẹn",
)
