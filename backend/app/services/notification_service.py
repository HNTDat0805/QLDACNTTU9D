import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlmodel import Session, col, func, select

from app.models import (
    Customer,
    Notification,
    NotificationCreate,
    NotificationPublic,
    NotificationsPublic,
    User,
)


def _get_user_customer_id(session: Session, user: User) -> uuid.UUID | None:
    """Tra cứu ID hồ sơ khách hàng liên kết với tài khoản người dùng."""
    customer = session.exec(
        select(Customer).where(col(Customer.user_id) == user.id)
    ).first()
    return customer.id if customer else None


def _is_notification_owner(
    session: Session,
    notification: Notification,
    user: User,
) -> bool:
    """Kiểm tra xem thông báo có thuộc về người dùng đang đăng nhập hay không."""
    if user.is_superuser:
        return True
    if notification.user_id == user.id:
        return True
    cust_id = _get_user_customer_id(session, user)
    if cust_id and notification.customer_id == cust_id:
        return True
    return False


def get_user_notifications(
    session: Session,
    current_user: User,
    is_read: bool | None = None,
    notification_type: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> NotificationsPublic:
    """
    Truy xuất danh sách thông báo của người dùng đang đăng nhập (Task 393).
    Hỗ trợ lọc theo trạng thái đọc (is_read), loại thông báo (notification_type),
    và phân trang kết quả.
    """
    cust_id = _get_user_customer_id(session, current_user)
    if cust_id:
        user_cond = or_(
            col(Notification.user_id) == current_user.id,
            col(Notification.customer_id) == cust_id,
        )
    else:
        user_cond = col(Notification.user_id) == current_user.id

    query = select(Notification).where(user_cond)
    count_query = select(func.count()).select_from(Notification).where(user_cond)

    # Đếm số lượng thông báo chưa đọc của người dùng
    unread_query = (
        select(func.count())
        .select_from(Notification)
        .where(user_cond, col(Notification.is_read).is_(False))
    )
    unread_count = session.exec(unread_query).one()

    if is_read is not None:
        query = query.where(col(Notification.is_read) == is_read)
        count_query = count_query.where(col(Notification.is_read) == is_read)

    if notification_type:
        query = query.where(col(Notification.notification_type) == notification_type)
        count_query = count_query.where(
            col(Notification.notification_type) == notification_type
        )

    total = session.exec(count_query).one()
    items = session.exec(
        query.order_by(col(Notification.created_at).desc()).offset(skip).limit(limit)
    ).all()

    data = [NotificationPublic.model_validate(n) for n in items]
    return NotificationsPublic(
        data=data,
        count=total,
        unread_count=unread_count,
    )


def get_unread_count(
    session: Session,
    current_user: User,
) -> int:
    """
    Truy xuất số lượng thông báo chưa đọc của người dùng hiện tại (Task 393).
    """
    cust_id = _get_user_customer_id(session, current_user)
    if cust_id:
        user_cond = or_(
            col(Notification.user_id) == current_user.id,
            col(Notification.customer_id) == cust_id,
        )
    else:
        user_cond = col(Notification.user_id) == current_user.id

    unread_query = (
        select(func.count())
        .select_from(Notification)
        .where(user_cond, col(Notification.is_read).is_(False))
    )
    return session.exec(unread_query).one()


def get_notification_by_id(
    session: Session,
    notification_id: uuid.UUID,
    current_user: User,
) -> NotificationPublic:
    """
    Truy xuất chi tiết một thông báo cụ thể (Task 393).
    Kiểm tra quyền truy cập: Trả về 403 nếu người dùng không sở hữu thông báo này.
    """
    notification = session.get(Notification, notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thông báo không tồn tại",
        )

    if not _is_notification_owner(session, notification, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập thông báo này",
        )

    return NotificationPublic.model_validate(notification)


def mark_as_read(
    session: Session,
    notification_id: uuid.UUID,
    current_user: User,
) -> NotificationPublic:
    """
    Đánh dấu một thông báo là đã đọc (Task 393).
    Kiểm tra quyền truy cập: Trả về 403 nếu người dùng không sở hữu thông báo này.
    """
    notification = session.get(Notification, notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thông báo không tồn tại",
        )

    if not _is_notification_owner(session, notification, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập thông báo này",
        )

    if not notification.is_read:
        notification.is_read = True
        session.add(notification)
        session.commit()
        session.refresh(notification)

    return NotificationPublic.model_validate(notification)


def mark_all_as_read(
    session: Session,
    current_user: User,
) -> int:
    """
    Đánh dấu tất cả thông báo chưa đọc của người dùng hiện tại là đã đọc (Task 393).
    Trả về số lượng thông báo đã được cập nhật.
    """
    cust_id = _get_user_customer_id(session, current_user)
    if cust_id:
        user_cond = or_(
            col(Notification.user_id) == current_user.id,
            col(Notification.customer_id) == cust_id,
        )
    else:
        user_cond = col(Notification.user_id) == current_user.id

    unread_notifications = session.exec(
        select(Notification).where(user_cond, col(Notification.is_read).is_(False))
    ).all()

    updated_count = len(unread_notifications)
    for n in unread_notifications:
        n.is_read = True
        session.add(n)

    if updated_count > 0:
        session.commit()

    return updated_count


def create_notification(
    session: Session,
    data: NotificationCreate,
) -> NotificationPublic:
    """
    Tạo mới một thông báo trong hệ thống.
    """
    notification = Notification(
        title=data.title,
        message=data.message,
        notification_type=data.notification_type,
        is_read=data.is_read,
        customer_id=data.customer_id,
        user_id=data.user_id,
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return NotificationPublic.model_validate(notification)
