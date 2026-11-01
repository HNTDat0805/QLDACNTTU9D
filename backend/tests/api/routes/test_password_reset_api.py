import secrets
from datetime import timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core import security
from app.core.security import verify_password
from app.models import (
    PasswordResetToken,
    RefreshToken,
    User,
    UserCreate,
    UserRole,
    get_datetime_utc,
)
from tests.utils.utils import random_email, random_lower_string


def create_test_user(
    db: Session,
    email: str | None = None,
    password: str | None = None,
    is_active: bool = True,
) -> tuple[User, str]:
    em = email or random_email()
    pwd = password or random_lower_string()
    user_in = UserCreate(
        email=em,
        password=pwd,
        role=UserRole.CUSTOMER.value,
        is_active=is_active,
        full_name="Test Password Reset User",
    )
    user = crud.create_user(session=db, user_create=user_in)
    return user, pwd


def test_forgot_password_registered_user(client: TestClient, db: Session) -> None:
    """
    Yêu cầu quên mật khẩu cho tài khoản tồn tại (Task 322):
    - Trả về thông báo thành công chung.
    - Lưu hash token vào database với thời hạn hợp lệ.
    """
    user, _ = create_test_user(db)
    from app.utils import EmailData

    captured_token = None

    def fake_email_gen(*, email_to: str, email: str, token: str) -> EmailData:
        nonlocal captured_token
        captured_token = token
        _ = email_to, email
        return EmailData(html_content="<p>Reset</p>", subject="Reset")

    with (
        patch(
            "app.services.password_reset_service.settings.SMTP_HOST", "smtp.test.com"
        ),
        patch(
            "app.services.password_reset_service.settings.EMAILS_FROM_EMAIL",
            "info@test.com",
        ),
        patch(
            "app.services.password_reset_service.generate_reset_password_email",
            side_effect=fake_email_gen,
        ),
        patch("app.services.password_reset_service.send_email", return_value=None),
    ):
        r = client.post(
            "/api/login/forgot-password",
            json={"email": user.email},
        )
        assert r.status_code == 200
        res = r.json()
        assert res["success"] is True
        assert (
            "Nếu thông tin định danh hợp lệ, hệ thống sẽ gửi hướng dẫn đặt lại mật khẩu đến bạn."
            in res["message"]
        )

        # Kiểm tra token đã được lưu dưới dạng hash trong DB
        db_token = db.exec(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.is_used == False,  # noqa: E712
            )
        ).first()
        assert db_token is not None
        assert captured_token is not None
        assert db_token.token_hash == security.hash_token(captured_token)
        assert db_token.is_used is False


def test_forgot_password_unregistered_email_anti_enumeration(
    client: TestClient,
) -> None:
    """
    Quên mật khẩu với email không tồn tại:
    - Trả về cùng một thông báo chung (chống rò rỉ tài khoản).
    - Không sinh token trong database.
    """
    non_existent = f"nonexistent_{secrets.token_hex(6)}@example.com"
    r = client.post(
        "/api/login/forgot-password",
        json={"email": non_existent},
    )
    assert r.status_code == 200
    res = r.json()
    assert res["success"] is True
    assert (
        "Nếu thông tin định danh hợp lệ, hệ thống sẽ gửi hướng dẫn đặt lại mật khẩu đến bạn."
        in res["message"]
    )


def test_forgot_password_inactive_user_does_not_generate_token(
    client: TestClient, db: Session
) -> None:
    """Tài khoản bị khóa yêu cầu quên mật khẩu không sinh token mới."""
    user, _ = create_test_user(db, is_active=False)
    r = client.post(
        "/api/login/forgot-password",
        json={"email": user.email},
    )
    assert r.status_code == 200
    # Không tạo token mới cho tài khoản inactive
    tokens = db.exec(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    ).all()
    assert len(tokens) == 0


def test_forgot_password_invalidates_previous_unused_tokens(
    client: TestClient, db: Session
) -> None:
    """Gửi yêu cầu quên mật khẩu mới sẽ vô hiệu hóa các mã chưa dùng trước đó."""
    user, _ = create_test_user(db)
    now = get_datetime_utc()

    # Tạo 1 token cũ chưa dùng
    old_raw = secrets.token_urlsafe(32)
    old_record = PasswordResetToken(
        user_id=user.id,
        token_hash=security.hash_token(old_raw),
        expires_at=now + timedelta(hours=2),
        is_used=False,
    )
    db.add(old_record)
    db.commit()

    # Yêu cầu quên mật khẩu mới
    r = client.post(
        "/api/login/forgot-password",
        json={"email": user.email},
    )
    assert r.status_code == 200

    # Token cũ phải bị đánh dấu is_used = True
    db.refresh(old_record)
    assert old_record.is_used is True


def test_verify_reset_token_valid(client: TestClient, db: Session) -> None:
    """Xác thực token hợp lệ thành công."""
    user, _ = create_test_user(db)
    raw_token = secrets.token_urlsafe(32)
    now = get_datetime_utc()

    db_token = PasswordResetToken(
        user_id=user.id,
        token_hash=security.hash_token(raw_token),
        expires_at=now + timedelta(hours=2),
        is_used=False,
    )
    db.add(db_token)
    db.commit()

    r = client.post(
        "/api/login/verify-reset-token",
        json={"token": raw_token},
    )
    assert r.status_code == 200
    res = r.json()
    assert res["success"] is True
    assert res["valid"] is True
    assert res["email"] == user.email


def test_verify_reset_token_invalid(client: TestClient) -> None:
    """Xác thực token không tồn tại trả về 400 Bad Request."""
    r = client.post(
        "/api/login/verify-reset-token",
        json={"token": "completely_invalid_random_token_12345"},
    )
    assert r.status_code == 400
    assert "Mã đặt lại mật khẩu không hợp lệ" in r.json()["detail"]


def test_verify_reset_token_already_used(client: TestClient, db: Session) -> None:
    """Xác thực token đã được sử dụng trả về 400."""
    user, _ = create_test_user(db)
    raw_token = secrets.token_urlsafe(32)
    now = get_datetime_utc()

    db_token = PasswordResetToken(
        user_id=user.id,
        token_hash=security.hash_token(raw_token),
        expires_at=now + timedelta(hours=2),
        is_used=True,
        used_at=now,
    )
    db.add(db_token)
    db.commit()

    r = client.post(
        "/api/login/verify-reset-token",
        json={"token": raw_token},
    )
    assert r.status_code == 400
    assert "Mã đặt lại mật khẩu đã được sử dụng" in r.json()["detail"]


def test_verify_reset_token_expired(client: TestClient, db: Session) -> None:
    """Xác thực token đã hết hạn trả về 400."""
    user, _ = create_test_user(db)
    raw_token = secrets.token_urlsafe(32)
    now = get_datetime_utc()

    db_token = PasswordResetToken(
        user_id=user.id,
        token_hash=security.hash_token(raw_token),
        expires_at=now - timedelta(minutes=5),  # Đã hết hạn 5 phút trước
        is_used=False,
    )
    db.add(db_token)
    db.commit()

    r = client.post(
        "/api/login/verify-reset-token",
        json={"token": raw_token},
    )
    assert r.status_code == 400
    assert "Mã đặt lại mật khẩu đã hết hạn" in r.json()["detail"]


def test_reset_password_success(client: TestClient, db: Session) -> None:
    """
    Đặt lại mật khẩu thành công (Task 322):
    - Cập nhật mật khẩu được mã hóa an toàn.
    - Đánh dấu token đã sử dụng (is_used=True, used_at).
    - Có thể đăng nhập bằng mật khẩu mới.
    - Mật khẩu cũ bị từ chối.
    """
    old_password = "OldPassword@123"
    user, _ = create_test_user(db, password=old_password)
    raw_token = secrets.token_urlsafe(32)
    now = get_datetime_utc()

    db_token = PasswordResetToken(
        user_id=user.id,
        token_hash=security.hash_token(raw_token),
        expires_at=now + timedelta(hours=2),
        is_used=False,
    )
    db.add(db_token)
    db.commit()

    new_password = "NewSecretPassword@456"
    r = client.post(
        "/api/login/reset-password",
        json={"token": raw_token, "new_password": new_password},
    )
    assert r.status_code == 200
    res = r.json()
    assert res["success"] is True
    assert "Đặt lại mật khẩu thành công" in res["message"]

    # Kiểm tra token đã đổi trạng thái is_used = True trong DB
    db.refresh(db_token)
    assert db_token.is_used is True
    assert db_token.used_at is not None

    # Kiểm tra mật khẩu trong DB đã thay đổi và hash an toàn
    db.refresh(user)
    is_valid_new, _ = verify_password(new_password, user.hashed_password)
    assert is_valid_new is True
    is_valid_old, _ = verify_password(old_password, user.hashed_password)
    assert is_valid_old is False

    # Thử đăng nhập bằng mật khẩu cũ -> Thất bại
    r_old = client.post(
        "/api/login/access-token",
        data={"username": user.email, "password": old_password},
    )
    assert r_old.status_code == 400

    # Thử đăng nhập bằng mật khẩu mới -> Thành công!
    r_new = client.post(
        "/api/login/access-token",
        data={"username": user.email, "password": new_password},
    )
    assert r_new.status_code == 200
    assert "access_token" in r_new.json()


def test_reset_password_cannot_reuse_token(client: TestClient, db: Session) -> None:
    """Không cho phép sử dụng lại token sau khi đặt lại mật khẩu thành công."""
    user, _ = create_test_user(db)
    raw_token = secrets.token_urlsafe(32)
    now = get_datetime_utc()

    db_token = PasswordResetToken(
        user_id=user.id,
        token_hash=security.hash_token(raw_token),
        expires_at=now + timedelta(hours=2),
        is_used=False,
    )
    db.add(db_token)
    db.commit()

    # Lần 1: Đặt lại thành công
    r1 = client.post(
        "/api/login/reset-password",
        json={"token": raw_token, "new_password": "NewValidPassword1@"},
    )
    assert r1.status_code == 200

    # Lần 2: Sử dụng lại cùng token -> Bị từ chối (400)
    r2 = client.post(
        "/api/login/reset-password",
        json={"token": raw_token, "new_password": "AnotherNewPassword2@"},
    )
    assert r2.status_code == 400
    assert "Mã đặt lại mật khẩu đã được sử dụng" in r2.json()["detail"]


def test_reset_password_expired_token_rejected(client: TestClient, db: Session) -> None:
    """Đặt lại mật khẩu với token hết hạn bị từ chối (400)."""
    user, _ = create_test_user(db)
    raw_token = secrets.token_urlsafe(32)
    now = get_datetime_utc()

    db_token = PasswordResetToken(
        user_id=user.id,
        token_hash=security.hash_token(raw_token),
        expires_at=now - timedelta(hours=1),  # Hết hạn 1 tiếng trước
        is_used=False,
    )
    db.add(db_token)
    db.commit()

    r = client.post(
        "/api/login/reset-password",
        json={"token": raw_token, "new_password": "ValidNewPassword123@"},
    )
    assert r.status_code == 400
    assert "Mã đặt lại mật khẩu đã hết hạn" in r.json()["detail"]


def test_reset_password_same_as_old_password_rejected(
    client: TestClient, db: Session
) -> None:
    """Mật khẩu mới không được trùng với mật khẩu hiện tại (400)."""
    current_pwd = "CurrentPassword123@"
    user, _ = create_test_user(db, password=current_pwd)
    raw_token = secrets.token_urlsafe(32)
    now = get_datetime_utc()

    db_token = PasswordResetToken(
        user_id=user.id,
        token_hash=security.hash_token(raw_token),
        expires_at=now + timedelta(hours=2),
        is_used=False,
    )
    db.add(db_token)
    db.commit()

    r = client.post(
        "/api/login/reset-password",
        json={"token": raw_token, "new_password": current_pwd},
    )
    assert r.status_code == 400
    assert "không được trùng với mật khẩu hiện tại" in r.json()["detail"]


def test_reset_password_for_locked_user_rejected(
    client: TestClient, db: Session
) -> None:
    """Tài khoản bị khóa không được phép đặt lại mật khẩu (400)."""
    user, _ = create_test_user(db, is_active=False)
    raw_token = secrets.token_urlsafe(32)
    now = get_datetime_utc()

    db_token = PasswordResetToken(
        user_id=user.id,
        token_hash=security.hash_token(raw_token),
        expires_at=now + timedelta(hours=2),
        is_used=False,
    )
    db.add(db_token)
    db.commit()

    r = client.post(
        "/api/login/reset-password",
        json={"token": raw_token, "new_password": "BrandNewPassword123@"},
    )
    assert r.status_code == 400
    assert "Tài khoản không hợp lệ hoặc đang bị khóa" in r.json()["detail"]


def test_reset_password_revokes_active_sessions(
    client: TestClient, db: Session
) -> None:
    """Đặt lại mật khẩu thành công sẽ thu hồi toàn bộ refresh token hiện có."""
    user, pwd = create_test_user(db)
    raw_token = secrets.token_urlsafe(32)
    now = get_datetime_utc()

    # User đăng nhập để tạo 1 refresh token
    login_resp = client.post(
        "/api/login/access-token",
        data={"username": user.email, "password": pwd},
    )
    assert login_resp.status_code == 200

    # Kiểm tra có refresh token active
    active_tokens = db.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.is_revoked == False,  # noqa: E712
        )
    ).all()
    assert len(active_tokens) >= 1

    # Tạo reset token
    db_token = PasswordResetToken(
        user_id=user.id,
        token_hash=security.hash_token(raw_token),
        expires_at=now + timedelta(hours=2),
        is_used=False,
    )
    db.add(db_token)
    db.commit()

    # Đặt lại mật khẩu
    r = client.post(
        "/api/login/reset-password",
        json={"token": raw_token, "new_password": "BrandNewPassword123@"},
    )
    assert r.status_code == 200

    # Toàn bộ refresh token của user phải bị thu hồi
    remaining_active = db.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.is_revoked == False,  # noqa: E712
        )
    ).all()
    assert len(remaining_active) == 0
