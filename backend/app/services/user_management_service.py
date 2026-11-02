import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlmodel import Session, col, func, select

from app import crud
from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.models import (
    RefreshToken,
    SystemLog,
    User,
    UserPublic,
    UserUpdate,
    get_datetime_utc,
)

logger = get_logger("app.services.user_management_service")


def list_users(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    role: str | None = None,
    is_active: bool | None = None,
    q: str | None = None,
) -> tuple[list[UserPublic], int]:
    """
    Truy vấn danh sách người dùng với phân trang và bộ lọc:
    - Lọc theo vai trò (role: customer, technician, staff, manager, admin).
    - Lọc theo trạng thái tài khoản (is_active: True/False).
    - Tìm kiếm theo từ khóa (q: email hoặc tên đầy đủ).
    """
    statement = select(User)
    count_statement = select(func.count()).select_from(User)

    conditions = []
    if role:
        conditions.append(col(User.role) == role.strip().lower())
    if is_active is not None:
        conditions.append(col(User.is_active) == is_active)
    if q and q.strip():
        term = q.strip()
        conditions.append(
            or_(
                col(User.email).ilike(f"%{term}%"),
                col(User.full_name).ilike(f"%{term}%"),
            )
        )

    for cond in conditions:
        statement = statement.where(cond)
        count_statement = count_statement.where(cond)

    count = session.exec(count_statement).one()
    users = session.exec(
        statement.order_by(col(User.created_at).desc()).offset(skip).limit(limit)
    ).all()

    users_public = [UserPublic.model_validate(u) for u in users]
    return users_public, count


def get_user_detail(
    session: Session,
    user_id: uuid.UUID,
    current_user: User,
) -> UserPublic:
    """
    Xem chi tiết thông tin tài khoản:
    - Cho phép chính người dùng sở hữu tài khoản xem.
    - Cho phép tài khoản có quyền quản lý (Admin, Manager, Superuser) xem bất kỳ tài khoản nào.
    - Người dùng thông thường cố truy cập tài khoản khác sẽ bị từ chối 403 Forbidden.
    """
    is_manager = current_user.is_superuser or (
        (current_user.role or "").lower() in ("admin", "manager")
    )
    if user_id != current_user.id and not is_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserPublic.model_validate(user)


def update_user(
    session: Session,
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: User,
) -> UserPublic:
    """
    Cập nhật thông tin tài khoản theo cấu trúc dữ liệu hiện có:
    - Quản lý có thể cập nhật thông tin người dùng.
    - Chặn cập nhật tài khoản Superuser nếu người gọi không phải Superuser.
    - Kiểm tra email không trùng với tài khoản khác.
    - Mã hóa mật khẩu nếu có thay đổi.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The user with this id does not exist in the system",
        )

    if db_user.is_superuser and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản Superuser mới có quyền sửa đổi thông tin của Superuser",
        )

    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

    user_data = user_in.model_dump(exclude_unset=True)
    if "password" in user_data and user_data["password"]:
        password = user_data.pop("password")
        user_data["hashed_password"] = get_password_hash(password)

    db_user.sqlmodel_update(user_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    logger.info(
        f"Cập nhật thành công tài khoản {db_user.email} (ID: {db_user.id}) bởi user={current_user.id}"
    )
    return UserPublic.model_validate(db_user)


def lock_user(
    session: Session,
    user_id: uuid.UUID,
    current_user: User,
    reason: str | None = None,
) -> UserPublic:
    """
    Khóa tài khoản (Task 321):
    - Kiểm tra quyền quản lý.
    - Chặn tự khóa tài khoản của chính mình (400 Bad Request).
    - Chặn khóa tài khoản Superuser (403 Forbidden).
    - Chặn Manager khóa Admin (403 Forbidden).
    - Đặt is_active = False.
    - Thu hồi toàn bộ Refresh Tokens của user bị khóa để vô hiệu hóa phiên làm việc ngay lập tức.
    - Ghi nhận lịch sử kiểm toán vào SystemLog.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tự khóa tài khoản của chính mình",
        )

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản người dùng cần khóa",
        )

    if user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không thể khóa tài khoản quản trị cấp cao (Superuser)",
        )

    # Manager không được khóa Admin
    if not current_user.is_superuser and current_user.role == "manager":
        if user.role == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Quản lý không có quyền khóa tài khoản Quản trị viên (Admin)",
            )

    now = get_datetime_utc()
    user.is_active = False
    session.add(user)

    # Thu hồi toàn bộ active refresh tokens để lập tức vô hiệu hóa các phiên đăng nhập
    active_tokens = session.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.is_revoked == False,  # noqa: E712
        )
    ).all()
    for token in active_tokens:
        token.is_revoked = True
        token.revoked_at = now
        session.add(token)

    # Ghi nhận nhật ký hệ thống
    reason_str = (
        reason.strip() if reason and reason.strip() else "Khóa bởi ban quản trị"
    )
    audit_log = SystemLog(
        action="LOCK_USER",
        entity_name="user",
        entity_id=str(user.id),
        details=f"Khóa tài khoản {user.email} bởi {current_user.email}. Lý do: {reason_str}",
        user_id=current_user.id,
        created_at=now,
    )
    session.add(audit_log)

    session.commit()
    session.refresh(user)

    logger.info(
        f"Khóa thành công tài khoản {user.email} (ID: {user.id}) bởi user={current_user.id}"
    )
    return UserPublic.model_validate(user)


def unlock_user(
    session: Session,
    user_id: uuid.UUID,
    current_user: User,
) -> UserPublic:
    """
    Mở khóa tài khoản (Task 321):
    - Kiểm tra quyền quản lý.
    - Cập nhật is_active = True.
    - Ghi nhận lịch sử kiểm toán vào SystemLog.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản người dùng cần mở khóa",
        )

    # Manager không được mở khóa Admin
    if not current_user.is_superuser and current_user.role == "manager":
        if user.role == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Quản lý không có quyền mở khóa tài khoản Quản trị viên (Admin)",
            )

    now = get_datetime_utc()
    user.is_active = True
    session.add(user)

    # Ghi nhận nhật ký hệ thống
    audit_log = SystemLog(
        action="UNLOCK_USER",
        entity_name="user",
        entity_id=str(user.id),
        details=f"Mở khóa tài khoản {user.email} bởi {current_user.email}",
        user_id=current_user.id,
        created_at=now,
    )
    session.add(audit_log)

    session.commit()
    session.refresh(user)

    logger.info(
        f"Mở khóa thành công tài khoản {user.email} (ID: {user.id}) bởi user={current_user.id}"
    )
    return UserPublic.model_validate(user)
