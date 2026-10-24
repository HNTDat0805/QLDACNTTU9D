import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.crud import create_user
from app.models import RefreshToken, User, UserCreate
from tests.utils.utils import random_email


def create_test_user(db: Session, is_active: bool = True) -> tuple[User, str]:
    email = random_email()
    password = "securePassword123"
    user_in = UserCreate(
        email=email,
        password=password,
        full_name="Nguyễn Văn Test",
        role="customer",
        is_active=is_active,
    )
    user = create_user(session=db, user_create=user_in)
    return user, password


# ==============================================================================
# REFRESH TOKEN LIFECYCLE, REVOCATION & ROTATION TESTS
# ==============================================================================


def test_refresh_token_valid_flow(client: TestClient, db: Session) -> None:
    """1. Refresh Token hợp lệ: Cấp Access Token mới và Refresh Token mới (Rotation)."""
    user, password = create_test_user(db)

    # Đăng nhập lấy cặp token ban đầu
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    assert login_res.status_code == 200
    r1 = login_res.json()["refresh_token"]
    assert r1 is not None

    # Làm mới token
    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": r1},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Kiểm tra claims của Access Token mới
    access_payload = security.decode_token(data["access_token"])
    assert access_payload["type"] == "access"
    assert access_payload["sub"] == str(user.id)
    assert access_payload["email"] == user.email
    assert access_payload["role"] == user.role

    # Kiểm tra claims của Refresh Token mới
    refresh_payload = security.decode_token(data["refresh_token"])
    assert refresh_payload["type"] == "refresh"
    assert refresh_payload["sub"] == str(user.id)
    assert "jti" in refresh_payload

    # Thử nghiệm sử dụng access token mới
    test_res = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert test_res.status_code == 200


def test_refresh_token_missing_field(client: TestClient) -> None:
    """2. Thiếu Refresh Token: Pydantic từ chối với mã 422 Unprocessable Entity."""
    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={},
    )
    assert res.status_code == 422


def test_refresh_token_malformed(client: TestClient) -> None:
    """3. Token sai định dạng: Từ chối với 401 Unauthorized."""
    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": "malformed.jwt.token.string"},
    )
    assert res.status_code == 401
    assert "Invalid refresh token" in res.json()["detail"]


def test_refresh_token_expired(client: TestClient, db: Session) -> None:
    """4. Token hết hạn: Từ chối với 401 Unauthorized."""
    user, _ = create_test_user(db)
    expired_token = security.create_refresh_token(
        subject=user.id,
        expires_delta=timedelta(seconds=-30),
    )
    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": expired_token},
    )
    assert res.status_code == 401
    assert "Invalid refresh token" in res.json()["detail"]


def test_refresh_token_invalid_signature(client: TestClient, db: Session) -> None:
    """5. Token sai chữ ký: Ký bằng khóa bí mật giả mạo -> 401 Unauthorized."""
    user, _ = create_test_user(db)
    payload = {
        "sub": str(user.id),
        "type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=7),
        "jti": uuid.uuid4().hex,
    }
    fake_token = jwt.encode(payload, "forged_secret_key_1234567890", algorithm="HS256")

    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": fake_token},
    )
    assert res.status_code == 401
    assert "Invalid refresh token" in res.json()["detail"]


def test_refresh_token_access_token_rejected(client: TestClient, db: Session) -> None:
    """6. Dùng Access Token thay Refresh Token: Từ chối vì sai loại token (401 Unauthorized)."""
    user, password = create_test_user(db)
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    access_token = login_res.json()["access_token"]

    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": access_token},
    )
    assert res.status_code == 401
    assert "refresh token required" in res.json()["detail"].lower()


def test_refresh_token_revoked_rejected(client: TestClient, db: Session) -> None:
    """7. Token đã bị thu hồi: Khi gọi /login/revoke-token, token không thể dùng để refresh nữa."""
    user, password = create_test_user(db)
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    refresh_token = login_res.json()["refresh_token"]

    # 1. Thu hồi token
    revoke_res = client.post(
        f"{settings.API_V1_STR}/login/revoke-token",
        json={"refresh_token": refresh_token},
    )
    assert revoke_res.status_code == 200
    assert "revoked successfully" in revoke_res.json()["message"]

    # 2. Cố gắng sử dụng token đã thu hồi
    refresh_res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 401
    assert "revoked" in refresh_res.json()["detail"].lower()


def test_refresh_token_inactive_user(client: TestClient, db: Session) -> None:
    """8. Người dùng không còn hợp lệ (inactive): Không cấp token mới (400 Bad Request)."""
    user, password = create_test_user(db)
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    refresh_token = login_res.json()["refresh_token"]

    # Khóa tài khoản người dùng
    user.is_active = False
    db.add(user)
    db.commit()

    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert res.status_code == 400
    assert "Inactive user" in res.json()["detail"]


def test_refresh_token_deleted_user(client: TestClient, db: Session) -> None:
    """8b. Người dùng đã bị xóa khỏi hệ thống: 401 Unauthorized."""
    user, password = create_test_user(db)
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    refresh_token = login_res.json()["refresh_token"]

    # Xóa người dùng khỏi DB
    db.delete(user)
    db.commit()

    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert res.status_code == 401
    assert "User not found" in res.json()["detail"]


def test_refresh_token_rotation_and_reuse_detection(
    client: TestClient, db: Session
) -> None:
    """9. Refresh Token Rotation & Reuse Detection (Chống Replay Attack):

    - Đăng nhập -> R1
    - Refresh hợp lệ -> R2 (R1 được đánh dấu là replaced_by_jti của R2)
    - Kẻ tấn công replay R1 -> Hệ thống phát hiện Reuse Detection, từ chối và thu hồi toàn bộ phiên
    - Client thử dùng R2 cũng bị từ chối vì phiên đã bị hủy do nghi vấn lộ token
    """
    user, password = create_test_user(db)
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    r1 = login_res.json()["refresh_token"]

    # Lần 1: Refresh bình thường bằng R1 -> Cấp R2
    ref1_res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": r1},
    )
    assert ref1_res.status_code == 200
    r2 = ref1_res.json()["refresh_token"]

    # Lần 2: Sử dụng lại R1 (Replay Attack)
    replay_res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": r1},
    )
    assert replay_res.status_code == 401
    assert "already used" in replay_res.json()["detail"].lower()

    # Kiểm tra trong DB: Cả R1 và R2 đều đã bị thu hồi
    r2_hash = security.hash_token(r2)
    db_r2 = db.exec(
        select(RefreshToken).where(RefreshToken.token_hash == r2_hash)
    ).first()
    assert db_r2 is not None
    assert db_r2.is_revoked is True

    # Thử dùng R2 lúc này cũng sẽ bị từ chối
    ref2_res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": r2},
    )
    assert ref2_res.status_code == 401


def test_refresh_token_database_rollback_on_error(
    monkeypatch, client: TestClient, db: Session
) -> None:
    """10. Cơ sở dữ liệu xảy ra lỗi: Xử lý lỗi an toàn 500, rollback transaction."""
    user, password = create_test_user(db)
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    refresh_token = login_res.json()["refresh_token"]

    original_commit = Session.commit

    def failing_commit(_self: Session) -> None:
        raise RuntimeError("Database connection interrupted")

    monkeypatch.setattr(Session, "commit", failing_commit)

    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert res.status_code == 500
    assert (
        "error occurred while processing refresh token" in res.json()["detail"].lower()
    )

    monkeypatch.setattr(Session, "commit", original_commit)


def test_refresh_token_alias_endpoint(client: TestClient, db: Session) -> None:
    """Kiểm tra gọi qua alias endpoint POST /api/login/refresh-token hoạt động chuẩn xác."""
    user, password = create_test_user(db)
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    refresh_token = login_res.json()["refresh_token"]

    res = client.post(
        "/api/login/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()
    assert "refresh_token" in res.json()
