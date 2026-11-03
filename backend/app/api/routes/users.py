import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import col, delete, select

from app import crud
from app.api.deps import (
    CurrentUser,
    RequireManager,
    SessionDep,
    get_current_active_superuser,
)
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import (
    Customer,
    Item,
    Message,
    UpdatePassword,
    User,
    UserCreate,
    UserLockRequest,
    UserLockResponse,
    UserPublic,
    UserRegister,
    UserRole,
    UsersPublic,
    UserUnlockResponse,
    UserUpdate,
    UserUpdateMe,
)
from app.services import user_management_service
from app.utils import generate_new_account_email, send_email

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    response_model=UsersPublic,
)
def read_users(
    session: SessionDep,
    _current_user: RequireManager,
    skip: int = 0,
    limit: int = 100,
    role: str | None = Query(
        None,
        description="Lọc theo vai trò: customer, technician, staff, manager, admin",
    ),
    is_active: bool | None = Query(
        None, description="Lọc theo trạng thái hoạt động (True/False)"
    ),
    q: str | None = Query(None, description="Tìm kiếm từ khóa theo email hoặc họ tên"),
) -> Any:
    """
    Lấy danh sách tài khoản (Task 321):
    - Hỗ trợ phân trang (skip, limit).
    - Lọc theo vai trò, trạng thái hoạt động và từ khóa tìm kiếm.
    - Yêu cầu quyền quản lý (Admin, Manager, Superuser).
    """
    users_public, count = user_management_service.list_users(
        session=session,
        skip=skip,
        limit=limit,
        role=role,
        is_active=is_active,
        q=q,
    )
    return UsersPublic(data=users_public, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic
)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    """
    Create new user.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = crud.create_user(session=session, user_create=user_in)
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password"
        )
    same_password, _ = verify_password(body.new_password, current_user.hashed_password)
    if body.current_password == body.new_password or same_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as the current one",
        )
    hashed_password = get_password_hash(body.new_password)
    try:
        current_user.hashed_password = hashed_password
        session.add(current_user)
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password due to database error",
        )
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate(
        email=user_in.email,
        password=user_in.password,
        full_name=user_in.full_name,
        role=UserRole.CUSTOMER.value,
        is_superuser=False,
    )
    user = crud.create_user(session=session, user_create=user_create)
    existing_customer = session.exec(
        select(Customer).where(
            Customer.email == user.email,
            col(Customer.user_id).is_(None),
        )
    ).first()
    if existing_customer:
        existing_customer.user_id = user.id
        session.add(existing_customer)
        session.commit()
    return user


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Xem thông tin chi tiết tài khoản (Task 321):
    - Cho phép chính người dùng xem thông tin của mình.
    - Cho phép quản lý (Admin, Manager, Superuser) xem bất kỳ tài khoản nào.
    - Chặn các tài khoản không có quyền xem thông tin người khác (403 Forbidden).
    """
    return user_management_service.get_user_detail(
        session=session, user_id=user_id, current_user=current_user
    )


@router.patch(
    "/{user_id}",
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: RequireManager,
) -> Any:
    """
    Cập nhật thông tin tài khoản (Task 321):
    - Yêu cầu quyền quản lý (Admin, Manager, Superuser).
    - Cập nhật thông tin theo cấu trúc dữ liệu hiện có (họ tên, email, vai trò, trạng thái, mật khẩu).
    """
    return user_management_service.update_user(
        session=session,
        user_id=user_id,
        user_in=user_in,
        current_user=current_user,
    )


@router.post(
    "/{user_id}/lock",
    response_model=UserLockResponse,
)
def lock_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    current_user: RequireManager,
    lock_data: UserLockRequest | None = None,
) -> Any:
    """
    Khóa tài khoản người dùng (Task 321):
    - Yêu cầu quyền quản lý (Admin, Manager, Superuser).
    - Chặn tự khóa chính mình (400 Bad Request).
    - Chặn khóa tài khoản Superuser (403 Forbidden).
    - Cập nhật is_active = False.
    - Thu hồi tất cả refresh token còn hiệu lực để ngắt phiên đăng nhập lập tức.
    - Tài khoản bị khóa sẽ không thể tiếp tục thực hiện các chức năng yêu cầu xác thực.
    """
    reason = lock_data.reason if lock_data else None
    user_public = user_management_service.lock_user(
        session=session,
        user_id=user_id,
        current_user=current_user,
        reason=reason,
    )
    return UserLockResponse(
        success=True,
        message=f"Đã khóa tài khoản {user_public.email} thành công",
        data=user_public,
    )


@router.post(
    "/{user_id}/unlock",
    response_model=UserUnlockResponse,
)
def unlock_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    current_user: RequireManager,
) -> Any:
    """
    Mở khóa tài khoản người dùng (Task 321):
    - Yêu cầu quyền quản lý (Admin, Manager, Superuser).
    - Cập nhật is_active = True.
    - Cho phép tài khoản hoạt động và đăng nhập bình thường trở lại.
    """
    user_public = user_management_service.unlock_user(
        session=session,
        user_id=user_id,
        current_user=current_user,
    )
    return UserUnlockResponse(
        success=True,
        message=f"Đã mở khóa tài khoản {user_public.email} thành công",
        data=user_public,
    )


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    statement = delete(Item).where(col(Item.owner_id) == user_id)
    session.exec(statement)
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")
