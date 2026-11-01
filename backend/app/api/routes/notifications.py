import uuid

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CurrentUser, RequireStaff, SessionDep
from app.models import (
    MarkAllReadResponse,
    NotificationCreate,
    NotificationPublic,
    NotificationsPublic,
    UnreadNotificationCount,
)
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=NotificationsPublic,
    status_code=status.HTTP_200_OK,
    summary="Truy xuất danh sách thông báo của người dùng (Task 393)",
    description="""
API lấy danh sách thông báo trong ứng dụng của người dùng đang đăng nhập:
- Chỉ trả về các thông báo thuộc sở hữu của tài khoản hiện tại.
- Hỗ trợ lọc theo trạng thái đã đọc (`is_read=true` hoặc `false`).
- Hỗ trợ lọc theo loại thông báo (`notification_type`).
- Trả về danh sách thông báo, tổng số lượng và số lượng thông báo chưa đọc.
""",
)
def get_user_notifications(
    session: SessionDep,
    current_user: CurrentUser,
    is_read: bool | None = Query(
        default=None, description="Lọc theo trạng thái đọc (True/False)"
    ),
    notification_type: str | None = Query(
        default=None, description="Lọc theo loại thông báo"
    ),
    skip: int = Query(default=0, ge=0, description="Vị trí bắt đầu"),
    limit: int = Query(default=20, ge=1, le=100, description="Số lượng bản ghi tối đa"),
) -> NotificationsPublic:
    return notification_service.get_user_notifications(
        session=session,
        current_user=current_user,
        is_read=is_read,
        notification_type=notification_type,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/unread-count",
    response_model=UnreadNotificationCount,
    status_code=status.HTTP_200_OK,
    summary="Truy xuất số lượng thông báo chưa đọc (Task 393)",
    description="Lấy tổng số lượng thông báo chưa đọc của tài khoản đang đăng nhập để hiển thị badge chuông thông báo.",
)
def get_unread_notification_count(
    session: SessionDep,
    current_user: CurrentUser,
) -> UnreadNotificationCount:
    count = notification_service.get_unread_count(
        session=session,
        current_user=current_user,
    )
    return UnreadNotificationCount(unread_count=count)


@router.patch(
    "/read-all",
    response_model=MarkAllReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Đánh dấu tất cả thông báo là đã đọc (Task 393)",
    description="Cập nhật toàn bộ các thông báo chưa đọc của tài khoản đang đăng nhập thành đã đọc.",
)
@router.post(
    "/read-all",
    response_model=MarkAllReadResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def mark_all_notifications_read(
    session: SessionDep,
    current_user: CurrentUser,
) -> MarkAllReadResponse:
    updated = notification_service.mark_all_as_read(
        session=session,
        current_user=current_user,
    )
    return MarkAllReadResponse(
        message="Đã đánh dấu tất cả thông báo là đã đọc",
        updated_count=updated,
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationPublic,
    status_code=status.HTTP_200_OK,
    summary="Truy xuất chi tiết thông báo (Task 393)",
    description="""
Xem nội dung chi tiết một thông báo:
- Kiểm tra quyền truy cập: Trả về 403 Forbidden nếu thông báo thuộc về người dùng khác.
- Trả về 404 Not Found nếu không tìm thấy thông báo.
""",
)
def get_notification_detail(
    session: SessionDep,
    current_user: CurrentUser,
    notification_id: uuid.UUID = Path(
        ..., description="Mã định danh duy nhất của thông báo"
    ),
) -> NotificationPublic:
    return notification_service.get_notification_by_id(
        session=session,
        notification_id=notification_id,
        current_user=current_user,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationPublic,
    status_code=status.HTTP_200_OK,
    summary="Đánh dấu một thông báo là đã đọc (Task 393)",
    description="""
Chuyển trạng thái thông báo thành đã đọc:
- Kiểm tra quyền truy cập: Không cho phép cập nhật thông báo của người dùng khác (403 Forbidden).
- Trả về 404 Not Found nếu không tìm thấy thông báo.
""",
)
@router.post(
    "/{notification_id}/read",
    response_model=NotificationPublic,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def mark_notification_read(
    session: SessionDep,
    current_user: CurrentUser,
    notification_id: uuid.UUID = Path(
        ..., description="Mã định danh duy nhất của thông báo"
    ),
) -> NotificationPublic:
    return notification_service.mark_as_read(
        session=session,
        notification_id=notification_id,
        current_user=current_user,
    )


@router.post(
    "",
    response_model=NotificationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo thông báo trong ứng dụng (Dành cho Quản trị/Nhân viên)",
    description="Cho phép nhân viên hoặc hệ thống tạo thông báo gửi đến người dùng cụ thể.",
)
def create_in_app_notification(
    session: SessionDep,
    _current_user: RequireStaff,
    body: NotificationCreate,
) -> NotificationPublic:
    return notification_service.create_notification(
        session=session,
        data=body,
    )
