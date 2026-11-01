"""Test suite for Task 371: Kiểm thử phân quyền, dữ liệu cá nhân và đầu vào API toàn hệ thống.

Contents:
Nhóm A: Kiểm thử phân quyền truy cập (AUTHZ)
  - AUTHZ-01: Truy cập API cần xác thực không có token -> Bị từ chối 401 Unauthorized.
  - AUTHZ-02: Truy cập API với token không hợp lệ (sai chữ ký, token rác, hết hạn) -> Bị từ chối 401 Unauthorized.
  - AUTHZ-03: Người dùng có vai trò hợp lệ được phép truy cập chức năng tương ứng (200/201).
  - AUTHZ-04: Khách hàng (Customer) không đủ quyền truy cập các endpoint quản lý/nhân viên -> Bị từ chối 403 Forbidden.
  - AUTHZ-05: Nhân viên (Staff) không đủ quyền truy cập các endpoint của quản lý (Manager/Admin) -> Bị từ chối 403 Forbidden.
  - AUTHZ-06: BOLA / IDOR - Customer A cố gắng truy cập hoặc chỉnh sửa hồ sơ khách hàng của Customer B -> Bị từ chối 403 Forbidden.
  - AUTHZ-07: BOLA / IDOR - Customer A cố gắng xem chi tiết lịch hẹn của Customer B -> Bị từ chối 403 Forbidden.
  - AUTHZ-08: BOLA / IDOR - Customer A cố gắng xem hoặc đánh dấu đã đọc thông báo của Customer B -> Bị từ chối 403 Forbidden.
  - AUTHZ-09: BOLA / IDOR - Customer A cố gắng cập nhật thiết bị của Customer B -> Bị từ chối 403 Forbidden.
  - AUTHZ-10: BOLA / IDOR - Customer A cố gắng duyệt báo giá sửa chữa của Customer B -> Bị từ chối 403 Forbidden.
  - AUTHZ-11: BOLA / IDOR - Customer A cố gắng gửi đánh giá cho lịch hẹn của Customer B -> Bị từ chối 403 Forbidden.

Nhóm B: Bảo vệ dữ liệu cá nhân (DATA)
  - DATA-01: Response của API User không làm lộ thông tin nhạy cảm (hashed_password, password, reset_token).
  - DATA-02: Ngăn chặn thu thập hàng loạt (scraping) danh sách dữ liệu cá nhân khách hàng (GET /api/customers cấm Customer).
  - DATA-03: Ngăn chặn người dùng xem thông tin chi tiết tài khoản của người khác qua ID (GET /api/v1/users/{id} cấm Customer khác).
  - DATA-04: Tra cứu tiến độ lịch hẹn chỉ trả về dữ liệu thuộc về khách hàng đang đăng nhập, không làm lộ lịch hẹn người khác.

Nhóm C: Kiểm tra và xác thực dữ liệu đầu vào (INPUT)
  - INPUT-01: Thiếu trường bắt buộc trong payload -> Trả về HTTP 422 Unprocessable Entity.
  - INPUT-02: Sai kiểu dữ liệu hoặc ID sai định dạng UUID -> Trả về HTTP 422 Unprocessable Entity.
  - INPUT-03: Giá trị vượt giới hạn cho phép (rating ngoài 1-5, số tiền <= 0, giá dịch vụ âm, SĐT < 8 ký tự) -> Bị từ chối 422/400.
  - INPUT-04: Chuỗi rỗng hoặc chỉ chứa khoảng trắng -> Bị từ chối hợp lệ 422/400.
  - INPUT-05: Ký tự đặc biệt, XSS payload và SQL Injection patterns được xử lý an toàn, không làm crash server (không lỗi 500).
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.crud import create_user
from app.models import (
    Appointment,
    AppointmentStatus,
    Customer,
    Device,
    Notification,
    Quote,
    QuoteStatus,
    User,
    UserCreate,
)
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
) -> tuple[User, dict[str, str]]:
    """Tạo nhanh tài khoản người dùng thực tế trong DB và trả về User cùng token headers."""
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
    headers = get_token_headers(user)
    return user, headers


# ============================================================================
# NHÓM A: KIỂM THỬ PHÂN QUYỀN TRUY CẬP (AUTHZ)
# ============================================================================


def test_authz_01_missing_token_access_denied(client: TestClient) -> None:
    """AUTHZ-01: Truy cập API cần đăng nhập mà không có token -> 401 Unauthorized."""
    endpoints = [
        ("GET", "/api/users/me"),
        ("GET", "/api/notifications"),
        ("GET", "/api/invoices"),
        ("POST", "/api/payments"),
        ("GET", "/api/customers"),
    ]
    for method, endpoint in endpoints:
        if method == "GET":
            res = client.get(endpoint)
        else:
            res = client.post(endpoint, json={})
        assert res.status_code == 401, (
            f"Endpoint {endpoint} phải yêu cầu token nhưng trả về {res.status_code}"
        )


def test_authz_02_invalid_or_expired_token_rejected(client: TestClient) -> None:
    """AUTHZ-02: Truy cập với token không hợp lệ hoặc hết hạn -> 401 Unauthorized."""
    # 1. Token rác không đúng cấu trúc JWT
    res1 = client.get(
        "/api/users/me", headers={"Authorization": "Bearer not-a-valid-jwt-token"}
    )
    assert res1.status_code == 401

    # 2. Token có chữ ký giả mạo (sai SECRET_KEY)
    fake_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "admin", "type": "access"},
        "wrong-secret-key-12345678901234567890",
        algorithm=security.ALGORITHM,
    )
    res2 = client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {fake_token}"}
    )
    assert res2.status_code == 401

    # 3. Token đã hết hạn trong quá khứ
    past_time = datetime.now(UTC) - timedelta(minutes=10)
    expired_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "role": "customer",
            "exp": past_time,
            "type": "access",
        },
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    res3 = client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert res3.status_code == 401


def test_authz_03_valid_role_access_granted(
    client: TestClient, db: Session
) -> None:
    """AUTHZ-03: Người dùng có vai trò hợp lệ được phép truy cập chức năng tương ứng."""
    # Customer truy cập /api/users/me và /api/notifications
    customer, cust_headers = create_test_user(db, role="customer")
    c_res = client.get("/api/users/me", headers=cust_headers)
    assert c_res.status_code == 200
    assert c_res.json()["email"] == customer.email

    notif_res = client.get("/api/notifications", headers=cust_headers)
    assert notif_res.status_code == 200

    # Staff truy cập /api/invoices
    _, staff_headers = create_test_user(db, role="staff")
    inv_res = client.get("/api/invoices", headers=staff_headers)
    assert inv_res.status_code == 200

    # Manager truy cập lấy danh mục dịch vụ
    _, mgr_headers = create_test_user(db, role="manager")
    svc_res = client.get("/api/services?include_inactive=true", headers=mgr_headers)
    assert svc_res.status_code == 200


def test_authz_04_insufficient_privileges_customer_accessing_staff_endpoints(
    client: TestClient, db: Session
) -> None:
    """AUTHZ-04: Khách hàng không đủ quyền truy cập các endpoint dành cho Staff/Manager/Admin -> 403 Forbidden."""
    _, cust_headers = create_test_user(db, role="customer")

    restricted_calls = [
        client.get("/api/customers", headers=cust_headers),
        client.post(
            "/api/customers",
            headers=cust_headers,
            json={"full_name": "Test", "phone_number": "0912345678"},
        ),
        client.get("/api/invoices", headers=cust_headers),
        client.post(
            "/api/invoices",
            headers=cust_headers,
            json={"repair_order_id": str(uuid.uuid4())},
        ),
        client.post(
            "/api/payments",
            headers=cust_headers,
            json={"invoice_id": str(uuid.uuid4()), "amount": 100000},
        ),
        client.post(
            "/api/services",
            headers=cust_headers,
            json={
                "name": "Sửa loa",
                "code": f"SPK-{uuid.uuid4().hex[:4]}",
                "base_price": 50000,
            },
        ),
        client.post(
            f"/api/v1/users/{uuid.uuid4()}/lock",
            headers=cust_headers,
            json={"reason": "Test"},
        ),
    ]
    for res in restricted_calls:
        assert res.status_code == 403, (
            f"Customer gọi endpoint quản lý nhưng không nhận 403, nhận: {res.status_code} - {res.text}"
        )


def test_authz_05_insufficient_privileges_staff_accessing_manager_endpoints(
    client: TestClient, db: Session
) -> None:
    """AUTHZ-05: Nhân viên thông thường (Staff) không đủ quyền truy cập các endpoint quản lý (Manager/Admin) -> 403 Forbidden."""
    _, staff_headers = create_test_user(db, role="staff")

    # Staff cố gắng tạo dịch vụ (RequireManager)
    res_svc = client.post(
        "/api/services",
        headers=staff_headers,
        json={
            "name": "Thay pin Pisen",
            "code": f"BAT-{uuid.uuid4().hex[:4]}",
            "base_price": 200000,
        },
    )
    assert res_svc.status_code == 403

    # Staff cố gắng khóa tài khoản (RequireManager)
    res_lock = client.post(
        f"/api/v1/users/{uuid.uuid4()}/lock",
        headers=staff_headers,
        json={"reason": "Khóa tài khoản bởi staff"},
    )
    assert res_lock.status_code == 403

    # Staff cố gắng xem danh sách tài khoản (RequireManager)
    res_users = client.get("/api/v1/users/", headers=staff_headers)
    assert res_users.status_code == 403


def test_authz_06_bola_customer_accessing_other_customer_profile(
    client: TestClient, db: Session
) -> None:
    """AUTHZ-06: BOLA - Customer A cố gắng xem hoặc cập nhật hồ sơ khách hàng của Customer B -> 403 Forbidden."""
    user_a, headers_a = create_test_user(db, role="customer")
    user_b, _ = create_test_user(db, role="customer")

    cust_a = Customer(
        full_name="Khách Hàng A",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
        user_id=user_a.id,
    )
    cust_b = Customer(
        full_name="Khách Hàng B",
        phone_number=f"092{uuid.uuid4().int % 10000000:07d}",
        user_id=user_b.id,
    )
    db.add(cust_a)
    db.add(cust_b)
    db.commit()
    db.refresh(cust_b)

    # 1. Customer A cố gắng đọc thông tin Customer B qua GET /api/customers/{customer_b_id}
    res_get = client.get(f"/api/customers/{cust_b.id}", headers=headers_a)
    assert res_get.status_code == 403
    assert "Không có quyền" in res_get.json()["detail"]

    # 2. Customer A cố gắng sửa thông tin Customer B qua PATCH /api/customers/{customer_b_id}
    res_patch = client.patch(
        f"/api/customers/{cust_b.id}",
        headers=headers_a,
        json={"full_name": "Tên Bị Sửa Trái Phép"},
    )
    assert res_patch.status_code == 403
    assert "Không có quyền" in res_patch.json()["detail"]


def test_authz_07_bola_customer_accessing_other_customer_appointment_detail(
    client: TestClient, db: Session
) -> None:
    """AUTHZ-07: BOLA - Customer A cố gắng xem chi tiết lịch hẹn của Customer B -> 403 Forbidden."""
    _, headers_a = create_test_user(db, role="customer")
    user_b, _ = create_test_user(db, role="customer")

    cust_b = Customer(
        full_name="Khách B",
        phone_number=f"093{uuid.uuid4().int % 10000000:07d}",
        user_id=user_b.id,
    )
    db.add(cust_b)
    db.commit()

    device_b = Device(customer_id=cust_b.id, brand="Apple", model="iPhone 13")
    db.add(device_b)
    db.commit()

    appt_b = Appointment(
        appointment_number=f"APPT-{uuid.uuid4().hex[:6].upper()}",
        appointment_date=datetime.now(UTC),
        status="IN_PROGRESS",
        customer_id=cust_b.id,
        device_id=device_b.id,
    )
    db.add(appt_b)
    db.commit()
    db.refresh(appt_b)

    # Customer A cố gắng truy cập chi tiết lịch hẹn của B
    res = client.get(f"/api/appointments/{appt_b.id}/detail", headers=headers_a)
    assert res.status_code == 403
    assert "Không có quyền" in res.json()["detail"]


def test_authz_08_bola_customer_accessing_other_customer_notifications(
    client: TestClient, db: Session
) -> None:
    """AUTHZ-08: BOLA - Customer A cố gắng xem hoặc đánh dấu đã đọc thông báo của Customer B -> 403 Forbidden."""
    _, headers_a = create_test_user(db, role="customer")
    user_b, _ = create_test_user(db, role="customer")

    notif_b = Notification(
        user_id=user_b.id,
        title="Thông báo riêng của B",
        message="Điện thoại của bạn đã sửa xong.",
        notification_type="STATUS_UPDATE",
        is_read=False,
    )
    db.add(notif_b)
    db.commit()
    db.refresh(notif_b)

    # 1. Customer A cố gắng xem chi tiết thông báo của B
    res_get = client.get(f"/api/notifications/{notif_b.id}", headers=headers_a)
    assert res_get.status_code == 403

    # 2. Customer A cố gắng đánh dấu đọc thông báo của B
    res_read = client.patch(
        f"/api/notifications/{notif_b.id}/read", headers=headers_a
    )
    assert res_read.status_code == 403


def test_authz_09_bola_customer_updating_other_customer_device(
    client: TestClient, db: Session
) -> None:
    """AUTHZ-09: BOLA - Customer A cố gắng cập nhật thiết bị của Customer B -> 403 Forbidden."""
    _, headers_a = create_test_user(db, role="customer")
    user_b, _ = create_test_user(db, role="customer")

    cust_b = Customer(
        full_name="Khách Hàng B",
        phone_number=f"095{uuid.uuid4().int % 10000000:07d}",
        user_id=user_b.id,
    )
    db.add(cust_b)
    db.commit()

    device_b = Device(
        customer_id=cust_b.id,
        brand="Samsung",
        model="Galaxy S22",
        color="Phantom Black",
    )
    db.add(device_b)
    db.commit()
    db.refresh(device_b)

    # Customer A cố gắng sửa màu thiết bị của B
    res = client.patch(
        f"/api/devices/{device_b.id}",
        headers=headers_a,
        json={"color": "Pink Gold"},
    )
    assert res.status_code == 403
    assert "không có quyền" in res.json()["detail"].lower()


def test_authz_10_bola_customer_approving_other_customer_quote(
    client: TestClient, db: Session
) -> None:
    """AUTHZ-10: BOLA - Customer A cố gắng duyệt báo giá của Customer B -> 403 Forbidden."""
    _, headers_a = create_test_user(db, role="customer")
    user_b, _ = create_test_user(db, role="customer")

    cust_b = Customer(
        full_name="Khách B",
        phone_number=f"096{uuid.uuid4().int % 10000000:07d}",
        user_id=user_b.id,
    )
    db.add(cust_b)
    db.commit()

    device_b = Device(customer_id=cust_b.id, brand="Apple", model="iPad Air")
    db.add(device_b)
    db.commit()

    appt_b = Appointment(
        appointment_number=f"APPT-{uuid.uuid4().hex[:6].upper()}",
        appointment_date=datetime.now(UTC),
        status="IN_PROGRESS",
        customer_id=cust_b.id,
        device_id=device_b.id,
    )
    db.add(appt_b)
    db.commit()

    quote_b = Quote(
        quote_number=f"BG-{uuid.uuid4().hex[:6].upper()}",
        appointment_id=appt_b.id,
        customer_id=cust_b.id,
        status=QuoteStatus.DRAFT.value,
        total_amount=500000.0,
    )
    db.add(quote_b)
    db.commit()
    db.refresh(quote_b)

    # Customer A cố gắng duyệt báo giá của B
    res = client.post(
        f"/api/quotes/{quote_b.id}/accept",
        headers=headers_a,
        json={"note": "Khách A duyệt lén"},
    )
    assert res.status_code == 403
    assert "không có quyền" in res.json()["detail"].lower()


def test_authz_11_bola_customer_reviewing_other_customer_appointment(
    client: TestClient, db: Session
) -> None:
    """AUTHZ-11: BOLA - Customer A cố gắng đánh giá lịch hẹn hoàn tất của Customer B -> 403 Forbidden."""
    _, headers_a = create_test_user(db, role="customer")
    user_b, _ = create_test_user(db, role="customer")

    cust_b = Customer(
        full_name="Khách B",
        phone_number=f"097{uuid.uuid4().int % 10000000:07d}",
        user_id=user_b.id,
    )
    db.add(cust_b)
    db.commit()

    device_b = Device(customer_id=cust_b.id, brand="Xiaomi", model="Redmi Note 12")
    db.add(device_b)
    db.commit()

    appt_b = Appointment(
        appointment_number=f"APPT-{uuid.uuid4().hex[:6].upper()}",
        appointment_date=datetime.now(UTC),
        status=AppointmentStatus.COMPLETED.value,
        customer_id=cust_b.id,
        device_id=device_b.id,
    )
    db.add(appt_b)
    db.commit()
    db.refresh(appt_b)

    # Customer A cố gửi đánh giá cho lịch hẹn của B
    res = client.post(
        "/api/reviews",
        headers=headers_a,
        json={
            "appointment_id": str(appt_b.id),
            "rating": 5,
            "comment": "Đánh giá mạo danh",
        },
    )
    assert res.status_code == 403
    assert "không có quyền" in res.json()["detail"].lower()


# ============================================================================
# NHÓM B: BẢO VỆ DỮ LIỆU CÁ NHÂN (DATA)
# ============================================================================


def test_data_01_no_password_or_hash_exposed_in_responses(
    client: TestClient, db: Session
) -> None:
    """DATA-01: Response của API User không bao giờ làm lộ password hay hashed_password."""
    user, headers = create_test_user(db, role="customer")

    # 1. Kiểm tra /api/users/me
    res_me = client.get("/api/users/me", headers=headers)
    assert res_me.status_code == 200
    data_me = res_me.json()
    assert "hashed_password" not in data_me
    assert "password" not in data_me

    # 2. Kiểm tra /api/v1/users/{id}
    res_id = client.get(f"/api/v1/users/{user.id}", headers=headers)
    assert res_id.status_code == 200
    data_id = res_id.json()
    assert "hashed_password" not in data_id
    assert "password" not in data_id

    # 3. Kiểm tra response đăng ký /api/v1/users/signup
    new_email = random_email()
    res_signup = client.post(
        "/api/v1/users/signup",
        json={
            "email": new_email,
            "password": "SecretPassword123!",
            "full_name": "Người Dùng Mới",
        },
    )
    assert res_signup.status_code == 200
    data_signup = res_signup.json()
    assert "hashed_password" not in data_signup
    assert "password" not in data_signup


def test_data_02_prevent_unauthorized_customer_data_scraping(
    client: TestClient, db: Session
) -> None:
    """DATA-02: Ngăn chặn thu thập hàng loạt (scraping) danh sách dữ liệu cá nhân khách hàng."""
    _, cust_headers = create_test_user(db, role="customer")

    # Customer thông thường cố gắng lấy danh bạ toàn bộ khách hàng
    res = client.get("/api/customers", headers=cust_headers)
    assert res.status_code == 403, (
        "Khách hàng không được phép lấy toàn bộ danh sách khách hàng khác"
    )


def test_data_03_prevent_viewing_other_user_account_detail(
    client: TestClient, db: Session
) -> None:
    """DATA-03: Ngăn chặn người dùng xem thông tin chi tiết tài khoản của người khác qua ID."""
    _, headers_a = create_test_user(db, role="customer")
    user_b, _ = create_test_user(db, role="customer")

    # Customer A cố tình gọi GET /api/v1/users/{user_b.id}
    res = client.get(f"/api/v1/users/{user_b.id}", headers=headers_a)
    assert res.status_code == 403


def test_data_04_appointment_lookup_scoped_to_current_customer(
    client: TestClient, db: Session
) -> None:
    """DATA-04: Tra cứu tiến độ lịch hẹn chỉ trả về dữ liệu của khách hàng đang đăng nhập, không làm lộ dữ liệu người khác."""
    user_a, headers_a = create_test_user(db, role="customer")
    user_b, _ = create_test_user(db, role="customer")

    cust_a = Customer(
        full_name="Khách A",
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
        user_id=user_a.id,
    )
    cust_b = Customer(
        full_name="Khách B",
        phone_number=f"099{uuid.uuid4().int % 10000000:07d}",
        user_id=user_b.id,
    )
    db.add(cust_a)
    db.add(cust_b)
    db.commit()

    device_b = Device(customer_id=cust_b.id, brand="Sony", model="Xperia 1")
    db.add(device_b)
    db.commit()

    appt_b = Appointment(
        appointment_number=f"APPT-{uuid.uuid4().hex[:6].upper()}",
        appointment_date=datetime.now(UTC),
        status="PENDING",
        customer_id=cust_b.id,
        device_id=device_b.id,
    )
    db.add(appt_b)
    db.commit()

    # Customer A tra cứu theo số điện thoại của Customer B
    res = client.get(
        "/api/appointments/history/lookup",
        params={"phone_number": cust_b.phone_number},
        headers=headers_a,
    )
    assert res.status_code == 200
    # Customer A không nhận được bất kỳ lịch hẹn nào của Customer B
    assert len(res.json()) == 0


# ============================================================================
# NHÓM C: KIỂM TRA VÀ XÁC THỰC DỮ LIỆU ĐẦU VÀO (INPUT)
# ============================================================================


def test_input_01_missing_required_fields_rejected(
    client: TestClient, db: Session
) -> None:
    """INPUT-01: Thiếu trường bắt buộc trong payload -> Trả về HTTP 422 Unprocessable Entity."""
    _, cust_headers = create_test_user(db, role="customer")
    _, staff_headers = create_test_user(db, role="staff")

    # 1. Đăng ký tài khoản thiếu email
    res1 = client.post("/api/v1/users/signup", json={"password": "Password123!"})
    assert res1.status_code == 422

    # 2. Đăng ký tài khoản thiếu password
    res2 = client.post(
        "/api/v1/users/signup", json={"email": "missing_pwd@example.com"}
    )
    assert res2.status_code == 422

    # 3. Gửi đánh giá thiếu rating
    res3 = client.post(
        "/api/reviews",
        headers=cust_headers,
        json={"appointment_id": str(uuid.uuid4()), "comment": "Tốt"},
    )
    assert res3.status_code == 422

    # 4. Ghi nhận thanh toán thiếu amount
    res4 = client.post(
        "/api/payments",
        headers=staff_headers,
        json={"invoice_id": str(uuid.uuid4()), "payment_method": "cash"},
    )
    assert res4.status_code == 422


def test_input_02_invalid_data_types_rejected(
    client: TestClient, db: Session
) -> None:
    """INPUT-02: Sai kiểu dữ liệu hoặc ID sai định dạng UUID -> Trả về HTTP 422 Unprocessable Entity."""
    _, cust_headers = create_test_user(db, role="customer")
    _, staff_headers = create_test_user(db, role="staff")

    # 1. Điểm đánh giá truyền string thay vì số nguyên
    res1 = client.post(
        "/api/reviews",
        headers=cust_headers,
        json={"appointment_id": str(uuid.uuid4()), "rating": "nam_sao"},
    )
    assert res1.status_code == 422

    # 2. Số tiền thanh toán truyền chuỗi không phải số thay vì float/number
    res2 = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(uuid.uuid4()),
            "amount": "khong_phai_so",
            "payment_method": "cash",
        },
    )
    assert res2.status_code == 422

    # 3. ID sai định dạng UUID trong Path parameter
    res3 = client.get("/api/customers/not-a-valid-uuid", headers=staff_headers)
    assert res3.status_code == 422


def test_input_03_out_of_range_values_rejected(
    client: TestClient, db: Session
) -> None:
    """INPUT-03: Giá trị vượt giới hạn cho phép (rating ngoài 1-5, amount <= 0, giá dịch vụ âm) -> Bị từ chối 422/400."""
    _, cust_headers = create_test_user(db, role="customer")
    _, staff_headers = create_test_user(db, role="staff")
    _, mgr_headers = create_test_user(db, role="manager")

    # 1. Rating < 1 hoặc > 5
    for invalid_rating in [0, 6, -1, 10]:
        res_r = client.post(
            "/api/reviews",
            headers=cust_headers,
            json={"appointment_id": str(uuid.uuid4()), "rating": invalid_rating},
        )
        assert res_r.status_code == 422

    # 2. Số tiền thanh toán <= 0
    for invalid_amt in [0, -50000]:
        res_p = client.post(
            "/api/payments",
            headers=staff_headers,
            json={
                "invoice_id": str(uuid.uuid4()),
                "amount": invalid_amt,
                "payment_method": "cash",
            },
        )
        assert res_p.status_code in (400, 422)

    # 3. Giá dịch vụ cơ sở < 0 (base_price < 0)
    res_s = client.post(
        "/api/services",
        headers=mgr_headers,
        json={
            "name": "Dịch vụ âm tiền",
            "code": f"NEG-{uuid.uuid4().hex[:4]}",
            "base_price": -10000,
        },
    )
    assert res_s.status_code == 422

    # 4. Số điện thoại quá ngắn (< 8 chữ số)
    res_c = client.post(
        "/api/customers",
        headers=staff_headers,
        json={"full_name": "Khách SĐT Ngắn", "phone_number": "123"},
    )
    assert res_c.status_code == 400


def test_input_04_blank_or_whitespace_strings_rejected(
    client: TestClient, db: Session
) -> None:
    """INPUT-04: Chuỗi rỗng hoặc chỉ chứa khoảng trắng -> Bị từ chối hợp lệ 422/400."""
    _, headers = create_test_user(db, role="customer", password="OldPassword123!")
    _, staff_headers = create_test_user(db, role="staff")

    # 1. Mật khẩu mới chỉ toàn khoảng trắng
    res_pwd = client.patch(
        "/api/users/me/password",
        headers=headers,
        json={"current_password": "OldPassword123!", "new_password": "        "},
    )
    assert res_pwd.status_code in (400, 422)

    # 2. Tạo khách hàng với SĐT chỉ toàn khoảng trắng
    res_cust = client.post(
        "/api/customers",
        headers=staff_headers,
        json={"full_name": "Khách Test", "phone_number": "        "},
    )
    assert res_cust.status_code in (400, 422)


def test_input_05_special_characters_sql_injection_xss_safe_handling(
    client: TestClient, db: Session
) -> None:
    """INPUT-05: Ký tự đặc biệt, XSS payload và SQL Injection patterns được xử lý an toàn, không làm crash server (không lỗi 500)."""
    _, staff_headers = create_test_user(db, role="staff")

    payloads = [
        "' OR '1'='1' --",
        "'; DROP TABLE user; --",
        "<script>alert('XSS')</script>",
        "../../../../etc/passwd",
        "${7*7}",
        "A" * 5000,  # Payload chuỗi dài
    ]

    for attack_payload in payloads:
        # 1. Thử vào ô tìm kiếm khách hàng q
        res_search = client.get(
            "/api/customers",
            params={"q": attack_payload},
            headers=staff_headers,
        )
        assert res_search.status_code in (200, 400, 422), (
            f"Server trả về lỗi không mong muốn {res_search.status_code} với payload {attack_payload}"
        )
        assert res_search.status_code != 500

        # 2. Thử vào ô ghi chú lịch hẹn tra cứu
        res_lookup = client.get(
            "/api/appointments/history/lookup",
            params={"appointment_number": attack_payload},
            headers=staff_headers,
        )
        assert res_lookup.status_code in (200, 400, 422)
        assert res_lookup.status_code != 500
