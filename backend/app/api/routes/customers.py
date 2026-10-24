import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CurrentUser, RequireManager, RequireStaff, SessionDep
from app.models import (
    AppointmentsHistoryPublic,
    CustomerCreate,
    CustomerPublic,
    CustomersPublic,
    CustomerUpdate,
    Message,
)
from app.services import customer_service, history_service

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get(
    "",
    response_model=CustomersPublic,
    summary="Lấy danh sách khách hàng",
)
def read_customers(
    session: SessionDep,
    _: RequireStaff,
    skip: int = Query(default=0, ge=0, description="Số lượng bản ghi bỏ qua"),
    limit: int = Query(default=20, ge=1, le=100, description="Số lượng bản ghi tối đa"),
    q: str | None = Query(
        default=None, description="Tìm kiếm theo tên, số điện thoại hoặc email"
    ),
) -> CustomersPublic:
    """API: Lấy danh sách khách hàng có phân trang và tìm kiếm theo tên, số điện thoại hoặc email."""
    return customer_service.get_customers(session=session, skip=skip, limit=limit, q=q)


@router.post(
    "",
    response_model=CustomerPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo khách hàng mới",
)
def create_customer(
    session: SessionDep,
    _: RequireStaff,
    body: CustomerCreate,
) -> CustomerPublic:
    """API: Tạo khách hàng mới với xác thực số điện thoại và kiểm tra trùng lặp."""
    return customer_service.create_customer(session=session, data=body)


@router.get(
    "/{customer_id}",
    response_model=CustomerPublic,
    summary="Xem chi tiết khách hàng",
)
def read_customer_by_id(
    session: SessionDep,
    current_user: CurrentUser,
    customer_id: Annotated[uuid.UUID, Path(description="Mã ID của khách hàng")],
) -> CustomerPublic:
    """API: Xem chi tiết thông tin khách hàng. Khách hàng thông thường chỉ có thể xem hồ sơ của mình."""
    return customer_service.get_customer_by_id(
        session=session, customer_id=customer_id, current_user=current_user
    )


@router.patch(
    "/{customer_id}",
    response_model=CustomerPublic,
    summary="Cập nhật thông tin khách hàng",
)
def update_customer(
    session: SessionDep,
    current_user: CurrentUser,
    customer_id: Annotated[uuid.UUID, Path(description="Mã ID của khách hàng")],
    body: CustomerUpdate,
) -> CustomerPublic:
    """API: Cập nhật thông tin khách hàng với kiểm tra trùng số điện thoại."""
    return customer_service.update_customer(
        session=session,
        customer_id=customer_id,
        data=body,
        current_user=current_user,
    )


@router.delete(
    "/{customer_id}",
    response_model=Message,
    summary="Xóa khách hàng",
)
def delete_customer(
    session: SessionDep,
    _: RequireManager,
    customer_id: Annotated[uuid.UUID, Path(description="Mã ID của khách hàng")],
) -> Message:
    """API: Xóa khách hàng khi không có dữ liệu lịch hẹn hoặc lịch sử sửa chữa liên quan."""
    return customer_service.delete_customer(session=session, customer_id=customer_id)


@router.get(
    "/{customer_id}/appointments",
    response_model=AppointmentsHistoryPublic,
    summary="Lấy lịch sử lịch hẹn của khách hàng",
)
def read_customer_appointments(
    session: SessionDep,
    current_user: CurrentUser,
    customer_id: Annotated[uuid.UUID, Path(description="Mã ID của khách hàng")],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, description="Lọc theo trạng thái"),
) -> AppointmentsHistoryPublic:
    """API: Tra cứu toàn bộ lịch sử lịch hẹn và sửa chữa của khách hàng."""
    return history_service.get_customer_appointment_history(
        session=session,
        customer_id=customer_id,
        skip=skip,
        limit=limit,
        status_filter=status,
        current_user=current_user,
    )
