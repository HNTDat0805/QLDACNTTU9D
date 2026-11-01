import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CurrentUserOptional, RequireManager, SessionDep
from app.models import (
    ServiceCreate,
    ServicePublic,
    ServicesPublic,
    ServiceUpdate,
)
from app.services import service_catalog_service

router = APIRouter(prefix="/services", tags=["services"])


@router.get(
    "/manage",
    response_model=ServicesPublic,
    summary="Lấy danh mục dịch vụ dành cho quản lý",
)
def read_managed_services(
    session: SessionDep,
    _: RequireManager,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ServicesPublic:
    """
    Trả về toàn bộ danh mục dịch vụ (kể cả đã ẩn) dành riêng cho người quản lý.
    """
    services, count = service_catalog_service.get_services(
        session=session,
        skip=skip,
        limit=limit,
        is_active=None,
    )
    return ServicesPublic(data=services, count=count)


@router.get(
    "",
    response_model=ServicesPublic,
    summary="Lấy danh mục dịch vụ sửa chữa",
)
def get_services(
    session: SessionDep,
    current_user: CurrentUserOptional = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    is_active: bool | None = Query(
        default=None, description="Lọc theo trạng thái hiển thị (True/False)"
    ),
    q: str | None = Query(
        default=None, description="Tìm kiếm từ khóa theo tên hoặc mã dịch vụ"
    ),
    include_inactive: bool = Query(
        default=False,
        description="Bao gồm cả các dịch vụ đã ẩn (chỉ dành cho ban quản lý)",
    ),
) -> ServicesPublic:
    """
    Lấy danh mục dịch vụ sửa chữa:
    - Đối với khách hàng / người dùng thông thường: Mặc định chỉ hiển thị các dịch vụ đang kinh doanh (is_active = True).
    - Dịch vụ bị ẩn sẽ không xuất hiện trong danh sách lựa chọn của khách hàng.
    - Quản lý có thể lọc hoặc chỉ định include_inactive=True để xem toàn bộ danh mục dịch vụ.
    """
    is_manager = False
    if current_user:
        is_manager = current_user.is_superuser or (
            (current_user.role or "").lower() in ("admin", "manager")
        )

    # Nếu không phải quản lý hoặc không yêu cầu xem dịch vụ ẩn: chỉ lấy dịch vụ active
    filter_active = is_active
    if not is_manager or not include_inactive:
        if filter_active is None:
            filter_active = True

    services, count = service_catalog_service.get_services(
        session=session,
        skip=skip,
        limit=limit,
        is_active=filter_active,
        q=q,
    )
    return ServicesPublic(data=services, count=count)


@router.get(
    "/{service_id}",
    response_model=ServicePublic,
    summary="Xem thông tin chi tiết một dịch vụ",
)
def get_service_by_id(
    session: SessionDep,
    service_id: Annotated[uuid.UUID, Path(description="Mã định danh ID của dịch vụ")],
) -> ServicePublic:
    """Xem chi tiết thông tin một dịch vụ sửa chữa theo ID."""
    return service_catalog_service.get_service_by_id(
        session=session, service_id=service_id
    )


@router.post(
    "",
    response_model=ServicePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo dịch vụ sửa chữa mới",
)
def create_service(
    session: SessionDep,
    current_user: RequireManager,
    body: ServiceCreate,
) -> ServicePublic:
    """
    Tạo dịch vụ sửa chữa mới:
    - Bắt buộc vai trò Quản lý (Admin / Manager).
    - Kiểm tra tên dịch vụ và mã dịch vụ không được để trống.
    - Kiểm tra mã dịch vụ và tên dịch vụ không bị trùng lặp (409 Conflict).
    - Kiểm tra giá khởi điểm (base_price >= 0) và thời gian dự kiến (estimated_duration_minutes > 0).
    - Trả về mã HTTP 201 Created cùng dữ liệu dịch vụ vừa tạo.
    """
    return service_catalog_service.create_service(
        session=session, data=body, current_user=current_user
    )


@router.put(
    "/{service_id}",
    response_model=ServicePublic,
    summary="Cập nhật thông tin dịch vụ sửa chữa (PUT)",
)
@router.patch(
    "/{service_id}",
    response_model=ServicePublic,
    summary="Cập nhật thông tin dịch vụ sửa chữa (PATCH)",
)
def update_service(
    session: SessionDep,
    current_user: RequireManager,
    service_id: Annotated[uuid.UUID, Path(description="Mã định danh ID của dịch vụ")],
    body: ServiceUpdate,
) -> ServicePublic:
    """
    Cập nhật thông tin dịch vụ sửa chữa:
    - Bắt buộc vai trò Quản lý (Admin / Manager).
    - Kiểm tra dịch vụ có tồn tại hay không (404 Not Found).
    - Cập nhật tên dịch vụ, giá dịch vụ, thời gian dự kiến và trạng thái.
    - Không tự ý thay đổi mã định danh của dịch vụ (code).
    - Không cho phép trùng tên với dịch vụ khác (409 Conflict).
    - Trả về dữ liệu mới nhất sau khi cập nhật (200 OK).
    """
    return service_catalog_service.update_service(
        session=session,
        service_id=service_id,
        data=body,
        current_user=current_user,
    )


@router.patch(
    "/{service_id}/hide",
    response_model=ServicePublic,
    summary="Ẩn dịch vụ sửa chữa (Soft Delete / Ngừng kinh doanh)",
)
@router.post(
    "/{service_id}/hide",
    response_model=ServicePublic,
    summary="Ẩn dịch vụ sửa chữa (Soft Delete / Ngừng kinh doanh)",
)
def hide_service(
    session: SessionDep,
    current_user: RequireManager,
    service_id: Annotated[uuid.UUID, Path(description="Mã định danh ID của dịch vụ")],
) -> ServicePublic:
    """
    Ẩn dịch vụ sửa chữa khỏi danh sách khách hàng có thể lựa chọn:
    - Bắt buộc vai trò Quản lý (Admin / Manager).
    - Kiểm tra dịch vụ tồn tại (404 Not Found).
    - Cập nhật trạng thái is_active = False (Soft Delete).
    - Dữ liệu dịch vụ vẫn được bảo toàn trong database và không làm mất liên kết với các lịch hẹn cũ.
    - Trả về dữ liệu dịch vụ với trạng thái is_active = False (200 OK).
    """
    return service_catalog_service.hide_service(
        session=session,
        service_id=service_id,
        current_user=current_user,
    )
