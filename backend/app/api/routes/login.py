import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import select

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core import security
from app.core.config import settings
from app.models import (
    Message,
    NewPassword,
    RefreshToken,
    RefreshTokenInput,
    Token,
    TokenPayload,
    User,
    UserCreate,
    UserPublic,
    UserRegister,
    UserRole,
    UserUpdate,
    get_datetime_utc,
)
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])


@router.post("/login/access-token")
def login_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token and refresh token for future requests
    """
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires, role=user.role, email=user.email
    )
    refresh_token = security.create_refresh_token(user.id)
    refresh_payload = security.decode_token(refresh_token)
    refresh_exp = datetime.fromtimestamp(refresh_payload["exp"], tz=UTC)
    refresh_jti = str(refresh_payload.get("jti", uuid.uuid4().hex))

    # Lưu bản ghi refresh token vào database (server-side tracking)
    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=security.hash_token(refresh_token),
        jti=refresh_jti,
        expires_at=refresh_exp,
        is_revoked=False,
    )
    session.add(db_refresh)
    session.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login/refresh-token", response_model=Token)
def refresh_access_token(session: SessionDep, body: RefreshTokenInput) -> Token:
    """Refresh access token using a valid refresh token.

    Thực hiện:
    1. Xác thực định dạng, chữ ký và thời hạn JWT.
    2. Kiểm tra loại token (bắt buộc type == "refresh").
    3. Kiểm tra người dùng trong cơ sở dữ liệu và trạng thái hoạt động.
    4. Kiểm tra trạng thái thu hồi trong DB (Server-Side Revocation).
    5. Phát hiện tái sử dụng token đã thay thế (Token Reuse Detection) và thu hồi phiên nếu có dấu hiệu tấn công.
    6. Thực hiện Refresh Token Rotation (thu hồi token cũ, cấp cặp token mới).
    """
    try:
        payload = security.decode_token(body.refresh_token)
        token_data = TokenPayload(**payload)
    except InvalidTokenError, ValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token_data.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not token_data.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = uuid.UUID(token_data.sub)
    except ValueError, TypeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    token_hash = security.hash_token(body.refresh_token)
    now = get_datetime_utc()

    try:
        stored_token = session.exec(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        ).first()

        if stored_token:
            # Kiểm tra nếu token đã bị thu hồi
            if stored_token.is_revoked:
                # REUSE DETECTION: Nếu token này đã được rotate (có replaced_by_jti),
                # có thể token cũ đã bị rò rỉ / kẻ tấn công replay.
                # Thu hồi toàn bộ active refresh tokens của user để bảo vệ tài khoản.
                if stored_token.replaced_by_jti is not None:
                    active_tokens = session.exec(
                        select(RefreshToken).where(
                            RefreshToken.user_id == user.id,
                            RefreshToken.is_revoked == False,  # noqa: E712
                        )
                    ).all()
                    for act in active_tokens:
                        act.is_revoked = True
                        act.revoked_at = now
                        session.add(act)
                    session.commit()
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token already used. All active sessions have been revoked for security.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token has been revoked",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

            # Kiểm tra thời hạn trong cơ sở dữ liệu
            token_expires_at = stored_token.expires_at
            if token_expires_at.tzinfo is None:
                token_expires_at = token_expires_at.replace(tzinfo=UTC)

            if token_expires_at < now:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Cấp access token mới và thực hiện Refresh Token Rotation
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = security.create_access_token(
            user.id,
            expires_delta=access_token_expires,
            role=user.role,
            email=user.email,
        )
        new_refresh_token = security.create_refresh_token(user.id)
        new_payload = security.decode_token(new_refresh_token)
        new_exp = datetime.fromtimestamp(new_payload["exp"], tz=UTC)
        new_jti = str(new_payload.get("jti", uuid.uuid4().hex))

        # Nếu token cũ có trong DB: đánh dấu đã thu hồi và gán replaced_by_jti
        if stored_token:
            stored_token.is_revoked = True
            stored_token.revoked_at = now
            stored_token.replaced_by_jti = new_jti
            session.add(stored_token)

        # Lưu token mới vào DB
        new_stored_token = RefreshToken(
            user_id=user.id,
            token_hash=security.hash_token(new_refresh_token),
            jti=new_jti,
            expires_at=new_exp,
            is_revoked=False,
        )
        session.add(new_stored_token)
        session.commit()

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing refresh token",
        ) from exc


@router.post("/login/revoke-token", response_model=Message)
def revoke_refresh_token(session: SessionDep, body: RefreshTokenInput) -> Message:
    """Thu hồi một Refresh Token (hỗ trợ đăng xuất an toàn)."""
    try:
        payload = security.decode_token(body.refresh_token)
        token_data = TokenPayload(**payload)
    except InvalidTokenError, ValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token_data.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_hash = security.hash_token(body.refresh_token)
    try:
        stored_token = session.exec(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        ).first()
        if stored_token:
            stored_token.is_revoked = True
            stored_token.revoked_at = get_datetime_utc()
            session.add(stored_token)
            session.commit()
        return Message(message="Refresh token revoked successfully")
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while revoking token",
        ) from exc


@router.post("/login/register", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Register a new customer account.
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
    return user


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    # Always return the same response to prevent email enumeration attacks
    # Only send email if user actually exists
    if user:
        password_reset_token = generate_password_reset_token(email=email)
        email_data = generate_reset_password_email(
            email_to=user.email, email=email, token=password_reset_token
        )
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(
        message="If that email is registered, we sent a password recovery link"
    )


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        # Don't reveal that the user doesn't exist - use same error as invalid token
        raise HTTPException(status_code=400, detail="Invalid token")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    user_in_update = UserUpdate(password=body.new_password)
    crud.update_user(
        session=session,
        db_user=user,
        user_in=user_in_update,
    )
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )
