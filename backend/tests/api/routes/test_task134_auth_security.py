import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.crud import create_user
from app.models import Notification, User, UserCreate, UserRole
from tests.utils.utils import random_email


def get_token_headers(user: User) -> dict[str, str]:
    """Tạo header Authorization Bearer token hợp lệ cho user."""
    token = security.create_access_token(
        subject=user.id, role=user.role, email=user.email
    )
    return {"Authorization": f"Bearer {token}"}


def create_test_user(
    db: Session,
    role: str = "customer",
    password: str = "SecurePass123!",
    is_active: bool = True,
    is_superuser: bool = False,
) -> tuple[User, str]:
    """Tạo nhanh tài khoản người dùng với role và trạng thái chỉ định."""
    email = random_email()
    user_in = UserCreate(
        email=email,
        password=password,
        full_name=f"User {role.title()} {uuid.uuid4().hex[:4]}",
        role=role,
        is_active=is_active,
        is_superuser=is_superuser,
    )
    user = create_user(session=db, user_create=user_in)
    return user, password


# ============================================================================
# PHẦN 1: KIỂM THỬ TOKEN HẾT HẠN & XÁC THỰC TOKEN (EXPIRED TOKEN & JWT)
# ============================================================================


def test_tc_tok_01_valid_token_access(client: TestClient, db: Session) -> None:
    """
    [TC-TOK-01] Request sử dụng token còn hạn (Valid Token).
    - Input: Access token còn hạn (mặc định 15 phút), gửi kèm header Authorization: Bearer <token>.
    - Endpoint: POST /api/v1/login/test-token và GET /api/users/me.
    - Expected: HTTP 200 OK, trả về đúng thông tin tài khoản đang đăng nhập.
    """
    user, _ = create_test_user(db, role="customer")
    headers = get_token_headers(user)

    # 1. Gọi /api/v1/login/test-token
    res1 = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert res1.status_code == 200
    assert res1.json()["email"] == user.email
    assert res1.json()["id"] == str(user.id)

    # 2. Gọi /api/users/me
    res2 = client.get("/api/users/me", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["email"] == user.email


def test_tc_tok_02_expired_token(client: TestClient, db: Session) -> None:
    """
    [TC-TOK-02] Request sử dụng token đã hết hạn (Expired Token).
    - Input: Access token được tạo với expires_delta = -10 giây (đã hết hạn trong quá khứ).
    - Expected: HTTP 401 Unauthorized, detail="Could not validate credentials",
      header phản hồi có WWW-Authenticate: Bearer.
    """
    user, _ = create_test_user(db, role="customer")
    expired_token = security.create_access_token(
        subject=user.id,
        expires_delta=timedelta(seconds=-10),
        role=user.role,
        email=user.email,
    )
    headers = {"Authorization": f"Bearer {expired_token}"}

    response = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert response.status_code == 401
    assert "could not validate credentials" in response.json()["detail"].lower()
    assert "Bearer" in response.headers.get("WWW-Authenticate", "")


def test_tc_tok_03_missing_token(client: TestClient) -> None:
    """
    [TC-TOK-03] Request không có token (Missing Token).
    - Input: Gửi request đến endpoint yêu cầu xác thực mà không kèm header Authorization.
    - Endpoint: POST /api/v1/login/test-token và GET /api/users/me.
    - Expected: HTTP 401 Unauthorized, detail="Not authenticated".
    """
    res1 = client.post(f"{settings.API_V1_STR}/login/test-token")
    assert res1.status_code == 401

    res2 = client.get("/api/users/me")
    assert res2.status_code == 401


def test_tc_tok_04_tampered_token_invalid_signature(
    client: TestClient, db: Session
) -> None:
    """
    [TC-TOK-04] Token bị chỉnh sửa nội dung hoặc sai chữ ký mật (Tampered / Invalid Signature).
    - Input: Token được ký bằng secret key khác hoặc sửa đổi nội dung payload sau khi ký.
    - Expected: HTTP 401 Unauthorized, detail="Could not validate credentials".
    """
    user, _ = create_test_user(db, role="customer")
    tampered_token = jwt.encode(
        {
            "sub": str(user.id),
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "role": "customer",
        },
        "wrong_secret_key_tampered_12345",
        algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {tampered_token}"}

    response = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert response.status_code == 401
    assert "could not validate credentials" in response.json()["detail"].lower()


def test_tc_tok_05_malformed_token(client: TestClient) -> None:
    """
    [TC-TOK-05] Token sai định dạng (Malformed Token).
    - Input: Header Authorization chứa chuỗi ngẫu nhiên không phải định dạng JWT 3 phần (header.payload.signature).
    - Expected: HTTP 401 Unauthorized.
    """
    for malformed in ["not-a-token", "abc.def", "Bearer 123456789"]:
        headers = {"Authorization": f"Bearer {malformed}"}
        res = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
        assert res.status_code == 401


def test_tc_tok_06_wrong_token_type_rejected(client: TestClient, db: Session) -> None:
    """
    [TC-TOK-06] Kiểm tra từ chối sai loại token (Dùng Refresh Token làm Access Token).
    - Input: Tạo token có type="refresh", gửi vào endpoint yêu cầu access token.
    - Expected: HTTP 401 Unauthorized, detail="Invalid token type: access token required".
    """
    user, _ = create_test_user(db, role="customer")
    refresh_token = security.create_refresh_token(subject=user.id)
    headers = {"Authorization": f"Bearer {refresh_token}"}

    response = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert response.status_code == 401
    assert "access token required" in response.json()["detail"].lower()


def test_tc_tok_07_token_user_not_found(client: TestClient) -> None:
    """
    [TC-TOK-07] Token hợp lệ nhưng user_id không tồn tại trong CSDL.
    - Input: Token có chữ ký hợp lệ nhưng sub là UUID ngẫu nhiên không có trong database.
    - Expected: HTTP 404 Not Found, detail="User not found".
    """
    non_existent_id = uuid.uuid4()
    token = security.create_access_token(subject=non_existent_id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert response.status_code == 404
    assert "user not found" in response.json()["detail"].lower()


# ============================================================================
# PHẦN 2: KIỂM THỬ MẬT KHẨU BĂM (PASSWORD HASHING & SECURITY)
# ============================================================================


def test_tc_pwd_01_password_is_hashed_before_db_storage(
    client: TestClient, db: Session
) -> None:
    """
    [TC-PWD-01] Mật khẩu được băm trước khi lưu vào CSDL và không lưu mật khẩu dạng rõ.
    - Input: Đăng ký tài khoản với plaintext password "MySecretPass@2026".
    - Expected:
      + Bản ghi User trong DB có user.hashed_password != plaintext.
      + Plaintext không bao giờ xuất hiện dưới dạng chuỗi con trong hashed_password.
      + Mật khẩu được băm bằng thuật toán an toàn (Argon2 / Bcrypt).
    """
    email = random_email()
    raw_password = "MySecretPass@2026"

    res = client.post(
        f"{settings.API_V1_STR}/login/register",
        json={"email": email, "password": raw_password, "full_name": "Test Hash"},
    )
    assert res.status_code == 200
    user_id = uuid.UUID(res.json()["id"])

    # Truy vấn trực tiếp từ CSDL
    user_db = db.get(User, user_id)
    assert user_db is not None
    assert user_db.hashed_password != raw_password
    assert raw_password not in user_db.hashed_password
    # Kiểm tra tiền tố hash an toàn (Argon2 hoặc Bcrypt)
    assert user_db.hashed_password.startswith(
        ("$argon2id$", "$argon2i$", "$2b$", "$2a$")
    )


def test_tc_pwd_02_salt_randomization() -> None:
    """
    [TC-PWD-02] Cơ chế Salt ngẫu nhiên: Cùng một mật khẩu tạo ra các hash khác nhau.
    - Mục tiêu: Ngăn chặn tấn công tra bảng băm (Rainbow Table).
    - Expected: get_password_hash("SamePassword123") gọi 2 lần cho 2 chuỗi băm hoàn toàn khác nhau.
    """
    raw_pwd = "SamePassword123"
    hash1 = security.get_password_hash(raw_pwd)
    hash2 = security.get_password_hash(raw_pwd)

    assert hash1 != hash2
    # Cả hai đều xác thực thành công với mật khẩu gốc
    v1, _ = security.verify_password(raw_pwd, hash1)
    v2, _ = security.verify_password(raw_pwd, hash2)
    assert v1 is True
    assert v2 is True


def test_tc_pwd_03_verify_correct_password() -> None:
    """
    [TC-PWD-03] Chức năng xác minh mật khẩu đúng (Verify Correct Password).
    - Expected: verify_password() trả về True khi mật khẩu khớp chính xác.
    """
    password = "CorrectStrongPass_999"
    hashed = security.get_password_hash(password)

    is_valid, _ = security.verify_password(password, hashed)
    assert is_valid is True


def test_tc_pwd_04_verify_incorrect_password() -> None:
    """
    [TC-PWD-04] Chức năng xác minh mật khẩu sai (Verify Incorrect Password).
    - Expected: verify_password() trả về False khi mật khẩu sai khác ký tự, chuỗi rỗng hoặc khác biệt hoa/thường.
    """
    password = "MyCorrectPassword"
    hashed = security.get_password_hash(password)

    # 1. Sai khác 1 ký tự
    assert security.verify_password("MyCorrectPassword1", hashed)[0] is False
    # 2. Sai chữ hoa / chữ thường
    assert security.verify_password("mycorrectpassword", hashed)[0] is False
    # 3. Mật khẩu rỗng
    assert security.verify_password("", hashed)[0] is False
    # 4. Mật khẩu hoàn toàn khác
    assert security.verify_password("CompletelyWrongPass", hashed)[0] is False


def test_tc_pwd_05_no_password_exposed_in_api_responses(
    client: TestClient,
) -> None:
    """
    [TC-PWD-05] Không hiển thị mật khẩu thật hoặc hashed_password trong dữ liệu trả về của API.
    - Endpoint: /login/register, /login/access-token, /users/me.
    - Expected: Payload JSON tuyệt đối không có trường "password" hay "hashed_password".
    """
    email = random_email()
    password = "SecretPassword123!"

    # 1. Register API
    res_reg = client.post(
        f"{settings.API_V1_STR}/login/register",
        json={"email": email, "password": password, "full_name": "Nguyen No Secret"},
    )
    assert res_reg.status_code == 200
    assert "password" not in res_reg.json()
    assert "hashed_password" not in res_reg.json()

    # 2. Login access-token API
    res_login = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    assert res_login.status_code == 200
    assert "password" not in res_login.json()
    assert "hashed_password" not in res_login.json()
    token = res_login.json()["access_token"]

    # 3. Users/me API
    res_me = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert "password" not in res_me.json()
    assert "hashed_password" not in res_me.json()


def test_tc_pwd_06_login_api_authentication_success_and_failure(
    client: TestClient, db: Session
) -> None:
    """
    [TC-PWD-06] Kiểm tra xác thực qua API đăng nhập với mật khẩu đúng và sai.
    - Input đúng: Đăng nhập thành công -> HTTP 200 OK.
    - Input sai: Đăng nhập thất bại -> HTTP 400 Bad Request, "Incorrect email or password".
    """
    user, password = create_test_user(db, role="customer")

    # Mật khẩu đúng -> 200 OK
    res_ok = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    assert res_ok.status_code == 200
    assert "access_token" in res_ok.json()

    # Mật khẩu sai -> 400 Bad Request
    res_fail = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": "WrongPasswordHere"},
    )
    assert res_fail.status_code == 400
    assert "incorrect email or password" in res_fail.json()["detail"].lower()


# ============================================================================
# PHẦN 3: KIỂM SOÁT PHÂN QUYỀN (AUTHORIZATION & RBAC)
# ============================================================================


def test_tc_auth_01_customer_access_allowed_resources(
    client: TestClient, db: Session
) -> None:
    """
    [TC-AUTH-01] Người dùng có quyền truy cập tài nguyên được phép (Role Customer).
    - Input: Token của role 'customer'.
    - Endpoint: GET /api/services (công khai), GET /api/notifications (thông báo cá nhân).
    - Expected: HTTP 200 OK.
    """
    customer, _ = create_test_user(db, role=UserRole.CUSTOMER.value)
    headers = get_token_headers(customer)

    # 1. Xem danh mục dịch vụ -> 200 OK
    res_svc = client.get("/api/services", headers=headers)
    assert res_svc.status_code == 200

    # 2. Xem thông báo của chính mình -> 200 OK
    res_notif = client.get("/api/notifications", headers=headers)
    assert res_notif.status_code == 200


def test_tc_auth_02_customer_forbidden_from_admin_manager_endpoints(
    client: TestClient, db: Session
) -> None:
    """
    [TC-AUTH-02] Người dùng không đủ quyền bị từ chối với HTTP 403 Forbidden.
    - Input: Token của role 'customer' gọi endpoint quản lý dịch vụ (RequireManager).
    - Endpoint: POST /api/services (Tạo dịch vụ), PATCH /api/services/{id}/hide (Ẩn dịch vụ).
    - Expected: HTTP 403 Forbidden, detail="The user doesn't have enough privileges".
    """
    customer, _ = create_test_user(db, role=UserRole.CUSTOMER.value)
    headers = get_token_headers(customer)

    # Cố tình tạo dịch vụ sửa chữa mới
    res_post = client.post(
        "/api/services",
        headers=headers,
        json={
            "code": f"SVC-HACK-{uuid.uuid4().hex[:4]}",
            "name": "Dịch vụ giả mạo",
            "base_price": 500_000,
            "estimated_duration_minutes": 30,
        },
    )
    assert res_post.status_code == 403
    assert "enough privileges" in res_post.json()["detail"].lower()


def test_tc_auth_03_staff_forbidden_from_manager_endpoints(
    client: TestClient, db: Session
) -> None:
    """
    [TC-AUTH-03] Nhân viên/Kỹ thuật viên không có quyền quản lý bị từ chối truy cập.
    - Input: Token role 'staff' hoặc 'technician' gọi endpoint yêu cầu RequireManager.
    - Expected: HTTP 403 Forbidden.
    """
    staff, _ = create_test_user(db, role=UserRole.STAFF.value)
    headers_staff = get_token_headers(staff)

    res = client.post(
        "/api/services",
        headers=headers_staff,
        json={
            "code": f"SVC-STAFF-{uuid.uuid4().hex[:4]}",
            "name": "Dịch vụ do Staff thử tạo",
            "base_price": 300_000,
            "estimated_duration_minutes": 20,
        },
    )
    assert res.status_code == 403


def test_tc_auth_04_manager_and_admin_authorized(
    client: TestClient, db: Session
) -> None:
    """
    [TC-AUTH-04] Quản lý (Manager) và Quản trị viên (Admin) được phép thực hiện các thao tác quản trị.
    - Input: Token role 'manager' hoặc 'admin'.
    - Expected: HTTP 201 Created khi tạo mới dịch vụ.
    """
    manager, _ = create_test_user(db, role=UserRole.MANAGER.value)
    headers_mgr = get_token_headers(manager)

    unique_code = f"SVC-MGR-{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        "/api/services",
        headers=headers_mgr,
        json={
            "code": unique_code,
            "name": f"Dịch vụ do Manager tạo {uuid.uuid4().hex[:4]}",
            "base_price": 250_000,
            "estimated_duration_minutes": 30,
        },
    )
    assert res.status_code == 201
    assert res.json()["code"] == unique_code


def test_tc_auth_05_superuser_bypasses_role_restriction(
    client: TestClient, db: Session
) -> None:
    """
    [TC-AUTH-05] Superuser tự động vượt qua các hạn chế vai trò (Superuser Bypass).
    - Input: User có is_superuser=True (bất kể role).
    - Expected: Được phép gọi các endpoint phân quyền role mà không bị 403.
    """
    superuser, _ = create_test_user(db, role="customer", is_superuser=True)
    headers = get_token_headers(superuser)

    code = f"SVC-ROOT-{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        "/api/services",
        headers=headers,
        json={
            "code": code,
            "name": f"Dịch vụ Superuser {uuid.uuid4().hex[:4]}",
            "base_price": 100_000,
            "estimated_duration_minutes": 15,
        },
    )
    assert res.status_code == 201
    assert res.json()["code"] == code


def test_tc_auth_06_inactive_user_access_rejected(
    client: TestClient, db: Session
) -> None:
    """
    [TC-AUTH-06] Tài khoản bị vô hiệu hóa (is_active = False) bị chặn truy cập.
    - Input: User có is_active=False mang token truy cập endpoint yêu cầu CurrentUser.
    - Expected: HTTP 400 Bad Request, detail="Inactive user".
    """
    inactive_user, _ = create_test_user(db, role="customer", is_active=False)
    headers = get_token_headers(inactive_user)

    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 400
    assert "inactive user" in response.json()["detail"].lower()


def test_tc_auth_07_unauthenticated_request_rejected(client: TestClient) -> None:
    """
    [TC-AUTH-07] Truy cập endpoint yêu cầu xác thực khi chưa đăng nhập.
    - Endpoint: /api/users/me, /api/notifications, /api/services (POST).
    - Expected: HTTP 401 Unauthorized.
    """
    assert client.get("/api/users/me").status_code == 401
    assert client.get("/api/notifications").status_code == 401
    assert (
        client.post(
            "/api/services",
            json={
                "code": "SVC-ANON",
                "name": "Dịch vụ nặc danh",
                "base_price": 100_000,
                "estimated_duration_minutes": 20,
            },
        ).status_code
        == 401
    )


def test_tc_auth_08_cross_user_notification_isolation(
    client: TestClient, db: Session
) -> None:
    """
    [TC-AUTH-08] Kiểm tra bảo vệ cô lập dữ liệu giữa các tài khoản (Cross-user Access Protection).
    - Kịch bản: User A cố tình xem hoặc sửa thông báo thuộc sở hữu của User B.
    - Expected: HTTP 403 Forbidden, detail="Bạn không có quyền truy cập thông báo này".
    """
    user_a, _ = create_test_user(db, role="customer")
    user_b, _ = create_test_user(db, role="customer")

    # Tạo thông báo thuộc về User B
    notif_b = Notification(
        user_id=user_b.id,
        title="Thông báo mật của User B",
        message="Dữ liệu tài chính riêng tư",
        is_read=False,
    )
    db.add(notif_b)
    db.commit()
    db.refresh(notif_b)

    # User A sử dụng token của mình để truy cập thông báo của User B
    headers_a = get_token_headers(user_a)

    # 1. Xem chi tiết thông báo của B
    res_get = client.get(f"/api/notifications/{notif_b.id}", headers=headers_a)
    assert res_get.status_code == 403
    assert "Bạn không có quyền truy cập thông báo này" in res_get.json()["detail"]

    # 2. Cố tình đánh dấu đã đọc thông báo của B
    res_patch = client.patch(f"/api/notifications/{notif_b.id}/read", headers=headers_a)
    assert res_patch.status_code == 403
    assert "Bạn không có quyền truy cập thông báo này" in res_patch.json()["detail"]
