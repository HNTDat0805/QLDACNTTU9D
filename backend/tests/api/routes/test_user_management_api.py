import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.models import RefreshToken, User, UserCreate, UserRole
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


def create_user_with_role(
    db: Session,
    role: str = UserRole.CUSTOMER.value,
    is_superuser: bool = False,
    is_active: bool = True,
    full_name: str | None = None,
) -> tuple[User, str]:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(
        email=email,
        password=password,
        role=role,
        is_superuser=is_superuser,
        is_active=is_active,
        full_name=full_name or f"User {role.capitalize()}",
    )
    user = crud.create_user(session=db, user_create=user_in)
    return user, password


def test_list_users_as_manager(client: TestClient, db: Session) -> None:
    """Kiểm tra quản lý (manager) lấy danh sách người dùng thành công."""
    manager, pwd = create_user_with_role(db, role=UserRole.MANAGER.value)
    headers = user_authentication_headers(
        client=client, email=manager.email, password=pwd
    )

    r = client.get("/api/users/?skip=0&limit=10", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data
    assert isinstance(data["data"], list)
    assert data["count"] >= 1


def test_list_users_filters(client: TestClient, db: Session) -> None:
    """Kiểm tra lọc danh sách người dùng theo vai trò, trạng thái và từ khóa."""
    admin, pwd = create_user_with_role(db, role=UserRole.ADMIN.value)
    unique_keyword = f"UniqueName_{uuid.uuid4().hex[:6]}"
    cust, _ = create_user_with_role(
        db,
        role=UserRole.CUSTOMER.value,
        is_active=True,
        full_name=unique_keyword,
    )
    headers = user_authentication_headers(
        client=client, email=admin.email, password=pwd
    )

    # Lọc theo vai trò customer
    r = client.get("/api/users/?role=customer", headers=headers)
    assert r.status_code == 200
    for u in r.json()["data"]:
        assert u["role"] == "customer"

    # Lọc theo từ khóa họ tên
    r = client.get(f"/api/users/?q={unique_keyword}", headers=headers)
    assert r.status_code == 200
    assert r.json()["count"] >= 1
    emails = [u["email"] for u in r.json()["data"]]
    assert cust.email in emails


def test_list_users_forbidden_for_customer(client: TestClient, db: Session) -> None:
    """Khách hàng thông thường không được phép xem danh sách người dùng (403)."""
    cust, pwd = create_user_with_role(db, role=UserRole.CUSTOMER.value)
    headers = user_authentication_headers(client=client, email=cust.email, password=pwd)

    r = client.get("/api/users/", headers=headers)
    assert r.status_code == 403


def test_get_user_detail_self(client: TestClient, db: Session) -> None:
    """Người dùng có thể xem chi tiết thông tin của chính mình."""
    cust, pwd = create_user_with_role(db, role=UserRole.CUSTOMER.value)
    headers = user_authentication_headers(client=client, email=cust.email, password=pwd)

    r = client.get(f"/api/users/{cust.id}", headers=headers)
    assert r.status_code == 200
    res_data = r.json()
    assert res_data["id"] == str(cust.id)
    assert res_data["email"] == cust.email


def test_get_user_detail_other_as_manager(client: TestClient, db: Session) -> None:
    """Quản lý có thể xem chi tiết thông tin tài khoản của người dùng khác."""
    manager, pwd = create_user_with_role(db, role=UserRole.MANAGER.value)
    cust, _ = create_user_with_role(db, role=UserRole.CUSTOMER.value)
    headers = user_authentication_headers(
        client=client, email=manager.email, password=pwd
    )

    r = client.get(f"/api/users/{cust.id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == str(cust.id)


def test_get_user_detail_other_as_customer_forbidden(
    client: TestClient, db: Session
) -> None:
    """Khách hàng không được xem chi tiết tài khoản của người khác (403)."""
    cust1, pwd1 = create_user_with_role(db, role=UserRole.CUSTOMER.value)
    cust2, _ = create_user_with_role(db, role=UserRole.CUSTOMER.value)
    headers = user_authentication_headers(
        client=client, email=cust1.email, password=pwd1
    )

    r = client.get(f"/api/users/{cust2.id}", headers=headers)
    assert r.status_code == 403


def test_update_user_as_manager(client: TestClient, db: Session) -> None:
    """Quản lý cập nhật thông tin tài khoản người dùng thành công."""
    manager, pwd = create_user_with_role(db, role=UserRole.MANAGER.value)
    cust, _ = create_user_with_role(db, role=UserRole.CUSTOMER.value)
    headers = user_authentication_headers(
        client=client, email=manager.email, password=pwd
    )

    new_name = f"Updated Name {uuid.uuid4().hex[:4]}"
    r = client.patch(
        f"/api/users/{cust.id}",
        headers=headers,
        json={"full_name": new_name},
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == new_name

    db.refresh(cust)
    assert cust.full_name == new_name


def test_lock_user_success_and_revoke_tokens(client: TestClient, db: Session) -> None:
    """
    Quản lý khóa tài khoản (Task 321):
    - Đặt is_active = False.
    - Thu hồi toàn bộ refresh token hiện có.
    """
    manager, pwd_mgr = create_user_with_role(db, role=UserRole.MANAGER.value)
    cust, pwd_cust = create_user_with_role(db, role=UserRole.CUSTOMER.value)

    # Đăng nhập bằng tài khoản cust để sinh refresh token
    login_resp = client.post(
        "/api/login/access-token",
        data={"username": cust.email, "password": pwd_cust},
    )
    assert login_resp.status_code == 200

    # Kiểm tra đã có refresh token active trong DB
    active_tokens_before = db.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == cust.id,
            RefreshToken.is_revoked == False,  # noqa: E712
        )
    ).all()
    assert len(active_tokens_before) >= 1

    # Manager thực hiện khóa tài khoản cust
    mgr_headers = user_authentication_headers(
        client=client, email=manager.email, password=pwd_mgr
    )
    lock_resp = client.post(
        f"/api/users/{cust.id}/lock",
        headers=mgr_headers,
        json={"reason": "Vi phạm quy định bảo mật hệ thống"},
    )
    assert lock_resp.status_code == 200
    res = lock_resp.json()
    assert res["success"] is True
    assert res["data"]["is_active"] is False

    # Xác nhận trong DB: user is_active == False
    db.refresh(cust)
    assert cust.is_active is False

    # Xác nhận toàn bộ refresh token đã bị thu hồi (is_revoked == True)
    active_tokens_after = db.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == cust.id,
            RefreshToken.is_revoked == False,  # noqa: E712
        )
    ).all()
    assert len(active_tokens_after) == 0


def test_locked_user_cannot_login(client: TestClient, db: Session) -> None:
    """Tài khoản đã bị khóa không thể đăng nhập (400 Inactive user)."""
    locked_user, pwd = create_user_with_role(
        db, role=UserRole.CUSTOMER.value, is_active=False
    )

    r = client.post(
        "/api/login/access-token",
        data={"username": locked_user.email, "password": pwd},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Inactive user"


def test_locked_user_blocked_from_authenticated_api(
    client: TestClient, db: Session
) -> None:
    """Tài khoản bị khóa trong lúc đang có access token cũng bị từ chối mọi API (400 Inactive user)."""
    user, pwd = create_user_with_role(db, role=UserRole.CUSTOMER.value, is_active=True)
    headers = user_authentication_headers(client=client, email=user.email, password=pwd)

    # Đang hoạt động -> truy cập me thành công
    r1 = client.get("/api/users/me", headers=headers)
    assert r1.status_code == 200

    # Khóa tài khoản trực tiếp trong DB
    user.is_active = False
    db.add(user)
    db.commit()

    # Truy cập lại bằng token cũ -> Bị từ chối
    r2 = client.get("/api/users/me", headers=headers)
    assert r2.status_code == 400
    assert r2.json()["detail"] == "Inactive user"


def test_lock_user_self_forbidden(client: TestClient, db: Session) -> None:
    """Người quản lý không được phép tự khóa tài khoản của chính mình (400)."""
    manager, pwd = create_user_with_role(db, role=UserRole.MANAGER.value)
    headers = user_authentication_headers(
        client=client, email=manager.email, password=pwd
    )

    r = client.post(f"/api/users/{manager.id}/lock", headers=headers)
    assert r.status_code == 400
    assert "Không thể tự khóa tài khoản của chính mình" in r.json()["detail"]


def test_lock_superuser_forbidden(client: TestClient, db: Session) -> None:
    """Không được phép khóa tài khoản Superuser (403)."""
    admin, pwd = create_user_with_role(db, role=UserRole.ADMIN.value)
    suser, _ = create_user_with_role(db, role=UserRole.ADMIN.value, is_superuser=True)
    headers = user_authentication_headers(
        client=client, email=admin.email, password=pwd
    )

    r = client.post(f"/api/users/{suser.id}/lock", headers=headers)
    assert r.status_code == 403
    assert "Không thể khóa tài khoản quản trị cấp cao" in r.json()["detail"]


def test_lock_user_by_customer_rejected(client: TestClient, db: Session) -> None:
    """Khách hàng không có quyền khóa tài khoản (403)."""
    cust1, pwd1 = create_user_with_role(db, role=UserRole.CUSTOMER.value)
    cust2, _ = create_user_with_role(db, role=UserRole.CUSTOMER.value)
    headers = user_authentication_headers(
        client=client, email=cust1.email, password=pwd1
    )

    r = client.post(f"/api/users/{cust2.id}/lock", headers=headers)
    assert r.status_code == 403


def test_unlock_user_success(client: TestClient, db: Session) -> None:
    """
    Quản lý mở khóa tài khoản (Task 321):
    - Đặt is_active = True.
    - Tài khoản có thể đăng nhập bình thường trở lại.
    """
    manager, pwd_mgr = create_user_with_role(db, role=UserRole.MANAGER.value)
    cust, pwd_cust = create_user_with_role(
        db, role=UserRole.CUSTOMER.value, is_active=False
    )

    # Đang khóa thì không đăng nhập được
    r_locked = client.post(
        "/api/login/access-token",
        data={"username": cust.email, "password": pwd_cust},
    )
    assert r_locked.status_code == 400

    # Quản lý mở khóa
    headers = user_authentication_headers(
        client=client, email=manager.email, password=pwd_mgr
    )
    r_unlock = client.post(f"/api/users/{cust.id}/unlock", headers=headers)
    assert r_unlock.status_code == 200
    res = r_unlock.json()
    assert res["success"] is True
    assert res["data"]["is_active"] is True

    # Xác nhận trong DB
    db.refresh(cust)
    assert cust.is_active is True

    # Giờ đây có thể đăng nhập thành công
    r_login = client.post(
        "/api/login/access-token",
        data={"username": cust.email, "password": pwd_cust},
    )
    assert r_login.status_code == 200
    assert "access_token" in r_login.json()


def test_unlock_user_by_customer_rejected(client: TestClient, db: Session) -> None:
    """Khách hàng không có quyền mở khóa tài khoản (403)."""
    cust1, pwd1 = create_user_with_role(db, role=UserRole.CUSTOMER.value)
    cust2, _ = create_user_with_role(db, role=UserRole.CUSTOMER.value, is_active=False)
    headers = user_authentication_headers(
        client=client, email=cust1.email, password=pwd1
    )

    r = client.post(f"/api/users/{cust2.id}/unlock", headers=headers)
    assert r.status_code == 403
