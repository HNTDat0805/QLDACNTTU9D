import secrets
from datetime import UTC, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app import crud
from app.core import security
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_password_hash, verify_password
from app.models import (
    PasswordResetToken,
    RefreshToken,
    SystemLog,
    User,
    get_datetime_utc,
)
from app.utils import generate_reset_password_email, send_email

logger = get_logger("app.services.password_reset_service")

GENERIC_FORGOT_PASSWORD_MESSAGE = "Nếu thông tin định danh hợp lệ, hệ thống sẽ gửi hướng dẫn đặt lại mật khẩu đến bạn."


def request_password_reset(session: Session, email: str) -> str:
    """
    Yêu cầu quên mật khẩu (Task 322):
    1. Kiểm tra tài khoản bằng email.
    2. Nếu tồn tại và đang hoạt động:
       - Vô hiệu hóa các token đặt lại mật khẩu cũ chưa sử dụng của user này.
       - Tạo token ngẫu nhiên an toàn bằng secrets.token_urlsafe(32).
       - Băm SHA-256 token và lưu vào database cùng thời hạn hết hạn (EMAIL_RESET_TOKEN_EXPIRE_HOURS).
       - Gửi token/liên kết đặt lại mật khẩu qua email nếu emails_enabled.
    3. Luôn trả về thông báo chung để không tiết lộ tài khoản có tồn tại hay không.
    """
    normalized_email = email.strip().lower()
    user = crud.get_user_by_email(session=session, email=normalized_email)

    if user and user.is_active:
        now = get_datetime_utc()
        # Vô hiệu hóa các mã đặt lại mật khẩu chưa sử dụng trước đó
        old_tokens = session.exec(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.is_used == False,  # noqa: E712
            )
        ).all()
        for old in old_tokens:
            old.is_used = True
            old.used_at = now
            session.add(old)

        # Tạo mã ngẫu nhiên bảo mật 32 bytes URL-safe
        raw_token = secrets.token_urlsafe(32)
        token_hash = security.hash_token(raw_token)
        expires_at = now + timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)

        token_record = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_used=False,
        )
        session.add(token_record)
        session.commit()

        # Gửi email nếu được cấu hình
        if settings.emails_enabled:
            try:
                email_data = generate_reset_password_email(
                    email_to=user.email, email=user.email, token=raw_token
                )
                send_email(
                    email_to=user.email,
                    subject=email_data.subject,
                    html_content=email_data.html_content,
                )
            except Exception as e:
                logger.error(
                    f"Không thể gửi email đặt lại mật khẩu cho {user.email}: {e}"
                )

        logger.info(
            f"Đã tạo mã đặt lại mật khẩu cho tài khoản {user.email} (expires_at={expires_at.isoformat()})"
        )

    return GENERIC_FORGOT_PASSWORD_MESSAGE


def verify_reset_token(session: Session, token: str) -> dict[str, Any]:
    """
    Xác thực token đặt lại mật khẩu (Task 322):
    - Kiểm tra token không hợp lệ (không tồn tại trong hệ thống).
    - Kiểm tra token đã được sử dụng.
    - Kiểm tra token đã hết hạn.
    - Kiểm tra tài khoản người dùng có tồn tại và đang hoạt động.
    """
    cleaned_token = token.strip()
    if not cleaned_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã đặt lại mật khẩu không được để trống",
        )

    token_hash = security.hash_token(cleaned_token)
    reset_token = session.exec(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã đặt lại mật khẩu không hợp lệ",
        )

    if reset_token.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã đặt lại mật khẩu đã được sử dụng. Vui lòng tạo yêu cầu mới.",
        )

    now = get_datetime_utc()
    token_exp = reset_token.expires_at
    if token_exp.tzinfo is None:
        token_exp = token_exp.replace(tzinfo=UTC)

    if token_exp < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã đặt lại mật khẩu đã hết hạn. Vui lòng tạo yêu cầu quên mật khẩu mới.",
        )

    user = session.get(User, reset_token.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản không hợp lệ hoặc đang bị khóa",
        )

    return {
        "valid": True,
        "email": user.email,
        "message": "Mã xác thực đặt lại mật khẩu hợp lệ",
    }


def reset_password_with_token(session: Session, token: str, new_password: str) -> bool:
    """
    Đặt lại mật khẩu mới (Task 322):
    1. Kiểm tra token có tồn tại, hợp lệ và chưa hết hạn.
    2. Khóa dòng bản ghi token (with_for_update) chống race conditions.
    3. Kiểm tra mật khẩu mới không trùng mật khẩu cũ.
    4. Mã hóa mật khẩu mới (argon2/bcrypt) và lưu vào database.
    5. Đánh dấu token đã sử dụng (is_used=True, used_at=now).
    6. Thu hồi toàn bộ active Refresh Tokens của người dùng để yêu cầu đăng nhập lại.
    7. Ghi nhận kiểm toán SystemLog.
    """
    cleaned_token = token.strip()
    if not cleaned_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã đặt lại mật khẩu không được để trống",
        )

    token_hash = security.hash_token(cleaned_token)
    reset_token = session.exec(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .with_for_update()
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã đặt lại mật khẩu không hợp lệ",
        )

    if reset_token.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã đặt lại mật khẩu đã được sử dụng. Vui lòng tạo yêu cầu mới.",
        )

    now = get_datetime_utc()
    token_exp = reset_token.expires_at
    if token_exp.tzinfo is None:
        token_exp = token_exp.replace(tzinfo=UTC)

    if token_exp < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã đặt lại mật khẩu đã hết hạn. Vui lòng tạo yêu cầu quên mật khẩu mới.",
        )

    user = session.get(User, reset_token.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản không hợp lệ hoặc đang bị khóa",
        )

    # Kiểm tra mật khẩu mới không được trùng mật khẩu hiện tại
    verified, _ = verify_password(new_password, user.hashed_password)
    if verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới không được trùng với mật khẩu hiện tại",
        )

    # Mã hóa mật khẩu mới
    user.hashed_password = get_password_hash(new_password)
    session.add(user)

    # Đánh dấu token đã được sử dụng
    reset_token.is_used = True
    reset_token.used_at = now
    session.add(reset_token)

    # Thu hồi tất cả Refresh Token còn hiệu lực của user
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

    # Ghi nhận nhật ký hệ thống
    audit_log = SystemLog(
        action="RESET_PASSWORD",
        entity_name="user",
        entity_id=str(user.id),
        details=f"Đặt lại mật khẩu thành công qua mã xác thực cho tài khoản {user.email}",
        user_id=user.id,
        created_at=now,
    )
    session.add(audit_log)

    session.commit()
    session.refresh(user)

    logger.info(
        f"Đặt lại mật khẩu thành công cho tài khoản {user.email} (ID: {user.id})"
    )
    return True
