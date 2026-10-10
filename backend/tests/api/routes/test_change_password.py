import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core import security
from app.core.config import settings
from app.core.security import verify_password
from app.models import UserCreate
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email


def test_change_password_success(client: TestClient, db: Session) -> None:
    """1. Đổi mật khẩu thành công: Người dùng đã đăng nhập đổi mật khẩu hợp lệ."""
    email = random_email()
    old_password = "CurrentPassword123!"
    new_password = "NewPassword123!"

    user_in = UserCreate(email=email, password=old_password)
    user = crud.create_user(session=db, user_create=user_in)

    headers = user_authentication_headers(
        client=client, email=email, password=old_password
    )

    response = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={"current_password": old_password, "new_password": new_password},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Password updated successfully"

    # Kiểm tra database đã cập nhật hash mật khẩu mới
    db.refresh(user)
    verified, _ = verify_password(new_password, user.hashed_password)
    assert verified is True


def test_change_password_incorrect_current_password(
    client: TestClient, db: Session
) -> None:
    """2. Mật khẩu hiện tại không chính xác: Từ chối yêu cầu và giữ nguyên mật khẩu cũ."""
    email = random_email()
    actual_password = "CurrentPassword123!"
    wrong_current_password = "WrongPassword999!"
    new_password = "NewPassword123!"

    user_in = UserCreate(email=email, password=actual_password)
    user = crud.create_user(session=db, user_create=user_in)

    headers = user_authentication_headers(
        client=client, email=email, password=actual_password
    )

    response = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={
            "current_password": wrong_current_password,
            "new_password": new_password,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect password"

    # Database vẫn giữ mật khẩu cũ
    db.refresh(user)
    verified_old, _ = verify_password(actual_password, user.hashed_password)
    assert verified_old is True


def test_change_password_missing_current_password(
    client: TestClient, db: Session
) -> None:
    """3. Thiếu mật khẩu hiện tại: Trả về lỗi 422 Unprocessable Entity."""
    email = random_email()
    password = "CurrentPassword123!"

    user_in = UserCreate(email=email, password=password)
    crud.create_user(session=db, user_create=user_in)

    headers = user_authentication_headers(client=client, email=email, password=password)

    response = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={"new_password": "NewPassword123!"},
    )

    assert response.status_code == 422


def test_change_password_missing_new_password(client: TestClient, db: Session) -> None:
    """4. Thiếu mật khẩu mới: Trả về lỗi 422 Unprocessable Entity."""
    email = random_email()
    password = "CurrentPassword123!"

    user_in = UserCreate(email=email, password=password)
    crud.create_user(session=db, user_create=user_in)

    headers = user_authentication_headers(client=client, email=email, password=password)

    response = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={"current_password": password},
    )

    assert response.status_code == 422


def test_change_password_policy_violation(client: TestClient, db: Session) -> None:
    """5. Mật khẩu mới không đạt chính sách: Độ dài < 8 ký tự hoặc toàn khoảng trắng."""
    email = random_email()
    password = "CurrentPassword123!"

    user_in = UserCreate(email=email, password=password)
    crud.create_user(session=db, user_create=user_in)

    headers = user_authentication_headers(client=client, email=email, password=password)

    # Thử mật khẩu quá ngắn (< 8 ký tự)
    response_short = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={"current_password": password, "new_password": "short"},
    )
    assert response_short.status_code == 422

    # Thử mật khẩu toàn khoảng trắng (whitespace-only)
    response_spaces = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={"current_password": password, "new_password": "        "},
    )
    assert response_spaces.status_code == 422


def test_change_password_same_as_current(client: TestClient, db: Session) -> None:
    """6. Mật khẩu mới trùng mật khẩu hiện tại: Trả về lỗi 400 Bad Request."""
    email = random_email()
    password = "CurrentPassword123!"

    user_in = UserCreate(email=email, password=password)
    crud.create_user(session=db, user_create=user_in)

    headers = user_authentication_headers(client=client, email=email, password=password)

    response = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={"current_password": password, "new_password": password},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "New password cannot be the same as the current one"
    )


def test_change_password_unauthenticated(client: TestClient) -> None:
    """7. Người dùng chưa đăng nhập: Không gửi Authorization header trả về 401."""
    response = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        json={
            "current_password": "CurrentPassword123!",
            "new_password": "NewPassword123!",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_change_password_user_not_found(client: TestClient) -> None:
    """8a. Tài khoản không còn tồn tại: Token trỏ tới UUID không có trong DB trả về 404."""
    non_existent_id = uuid.uuid4()
    token = security.create_access_token(non_existent_id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={
            "current_password": "CurrentPassword123!",
            "new_password": "NewPassword123!",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_change_password_user_inactive(client: TestClient, db: Session) -> None:
    """8b. Tài khoản không hợp lệ (bị vô hiệu hóa): Trả về 400 Inactive user."""
    email = random_email()
    password = "CurrentPassword123!"

    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    headers = user_authentication_headers(client=client, email=email, password=password)

    # Vô hiệu hóa tài khoản trong database
    user.is_active = False
    db.add(user)
    db.commit()

    response = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={
            "current_password": password,
            "new_password": "NewPassword123!",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"


def test_change_password_database_error_rollback(
    client: TestClient, db: Session
) -> None:
    """9. Database xảy ra lỗi khi cập nhật: Rollback và trả về 500 Internal Server Error."""
    email = random_email()
    old_password = "CurrentPassword123!"
    new_password = "NewPassword123!"

    user_in = UserCreate(email=email, password=old_password)
    user = crud.create_user(session=db, user_create=user_in)

    headers = user_authentication_headers(
        client=client, email=email, password=old_password
    )

    with patch("sqlmodel.Session.commit", side_effect=Exception("Database failure")):
        response = client.patch(
            f"{settings.API_V1_STR}/users/me/password",
            headers=headers,
            json={"current_password": old_password, "new_password": new_password},
        )

    assert response.status_code == 500
    assert (
        response.json()["detail"] == "Failed to update password due to database error"
    )

    # Đảm bảo mật khẩu không bị thay đổi trong database
    db.refresh(user)
    verified_old, _ = verify_password(old_password, user.hashed_password)
    assert verified_old is True


def test_change_password_verification_and_login_transition(
    client: TestClient, db: Session
) -> None:
    """10. Sau khi đổi mật khẩu, mật khẩu mới xác minh thành công và mật khẩu cũ không còn hợp lệ khi đăng nhập."""
    email = random_email()
    old_password = "CurrentPassword123!"
    new_password = "NewPassword123!"

    user_in = UserCreate(email=email, password=old_password)
    user = crud.create_user(session=db, user_create=user_in)

    # 1. Đăng nhập với mật khẩu cũ thành công
    headers = user_authentication_headers(
        client=client, email=email, password=old_password
    )

    # 2. Đổi mật khẩu
    response = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={"current_password": old_password, "new_password": new_password},
    )
    assert response.status_code == 200

    # 3. Mật khẩu mới xác minh thành công trong DB, mật khẩu cũ thất bại
    db.refresh(user)
    verified_new, _ = verify_password(new_password, user.hashed_password)
    verified_old, _ = verify_password(old_password, user.hashed_password)
    assert verified_new is True
    assert verified_old is False

    # 4. Thử đăng nhập lại bằng mật khẩu cũ -> Thất bại (400)
    failed_login = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": old_password},
    )
    assert failed_login.status_code == 400
    assert failed_login.json()["detail"] == "Incorrect email or password"

    # 5. Đăng nhập lại bằng mật khẩu mới -> Thành công (200)
    success_login = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": new_password},
    )
    assert success_login.status_code == 200
    assert "access_token" in success_login.json()
