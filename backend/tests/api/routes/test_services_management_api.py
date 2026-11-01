import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import security
from app.crud import create_user
from app.models import (
    Appointment,
    AppointmentService,
    Customer,
    Device,
    Service,
    Technician,
    User,
    UserCreate,
    UserRole,
)
from tests.utils.utils import random_email, random_lower_string


def get_auth_headers(user: User) -> dict[str, str]:
    token = security.create_access_token(
        subject=user.id, role=user.role, email=user.email
    )
    return {"Authorization": f"Bearer {token}"}


def create_role_user(db: Session, role: str) -> User:
    email = random_email()
    pwd = random_lower_string()
    user_in = UserCreate(
        email=email,
        password=pwd,
        full_name=f"Test {role.title()}",
        role=role,
        is_superuser=False,
    )
    return create_user(session=db, user_create=user_in)


def test_admin_create_service_success(client: TestClient, db: Session) -> None:
    """Admin tạo mới dịch vụ sửa chữa thành công (201 Created)."""
    admin = create_role_user(db, UserRole.ADMIN.value)
    headers = get_auth_headers(admin)

    unique_suffix = uuid.uuid4().hex[:6].upper()
    svc_code = f"SVC-TEST-{unique_suffix}"
    svc_name = f"Thay Màn Hình Pro Max {unique_suffix}"

    payload = {
        "code": svc_code,
        "name": svc_name,
        "description": "Thay màn hình chính hãng bảo hành 12 tháng",
        "base_price": 2_500_000.0,
        "estimated_duration_minutes": 60,
        "is_active": True,
    }

    r = client.post("/api/services", headers=headers, json=payload)
    assert r.status_code == 201
    res = r.json()
    assert res["code"] == svc_code
    assert res["name"] == svc_name
    assert res["base_price"] == 2_500_000.0
    assert res["estimated_duration_minutes"] == 60
    assert res["is_active"] is True
    assert "id" in res

    # Kiểm tra trong database
    db_svc = db.get(Service, uuid.UUID(res["id"]))
    assert db_svc is not None
    assert db_svc.code == svc_code
    assert db_svc.name == svc_name


def test_admin_create_service_invalid_data(client: TestClient, db: Session) -> None:
    """Admin tạo dịch vụ với dữ liệu không hợp lệ -> 422 Unprocessable Entity."""
    admin = create_role_user(db, UserRole.ADMIN.value)
    headers = get_auth_headers(admin)

    # 1. Tên dịch vụ rỗng
    r1 = client.post(
        "/api/services",
        headers=headers,
        json={
            "code": f"SVC-ERR-{uuid.uuid4().hex[:4]}",
            "name": "   ",
            "base_price": 100_000,
            "estimated_duration_minutes": 30,
        },
    )
    assert r1.status_code == 422

    # 2. Giá dịch vụ âm (< 0)
    r2 = client.post(
        "/api/services",
        headers=headers,
        json={
            "code": f"SVC-ERR-{uuid.uuid4().hex[:4]}",
            "name": "Dịch vụ giá âm",
            "base_price": -50_000,
            "estimated_duration_minutes": 30,
        },
    )
    assert r2.status_code == 422

    # 3. Thời gian dự kiến <= 0
    r3 = client.post(
        "/api/services",
        headers=headers,
        json={
            "code": f"SVC-ERR-{uuid.uuid4().hex[:4]}",
            "name": "Dịch vụ thời gian 0",
            "base_price": 100_000,
            "estimated_duration_minutes": 0,
        },
    )
    assert r3.status_code == 422

    # 4. Mã dịch vụ rỗng
    r4 = client.post(
        "/api/services",
        headers=headers,
        json={
            "code": "",
            "name": "Dịch vụ mã rỗng",
            "base_price": 100_000,
            "estimated_duration_minutes": 30,
        },
    )
    assert r4.status_code == 422


def test_create_service_duplicate_code(client: TestClient, db: Session) -> None:
    """Tạo dịch vụ với mã dịch vụ đã tồn tại -> 409 Conflict."""
    admin = create_role_user(db, UserRole.ADMIN.value)
    headers = get_auth_headers(admin)

    unique_code = f"SVC-DUP-{uuid.uuid4().hex[:6].upper()}"

    # Lần 1: Thành công
    r1 = client.post(
        "/api/services",
        headers=headers,
        json={
            "code": unique_code,
            "name": f"Dịch vụ 1 {uuid.uuid4().hex[:4]}",
            "base_price": 200_000,
            "estimated_duration_minutes": 30,
        },
    )
    assert r1.status_code == 201

    # Lần 2: Trùng mã code -> 409 Conflict
    r2 = client.post(
        "/api/services",
        headers=headers,
        json={
            "code": unique_code,
            "name": f"Dịch vụ 2 {uuid.uuid4().hex[:4]}",
            "base_price": 300_000,
            "estimated_duration_minutes": 45,
        },
    )
    assert r2.status_code == 409
    assert f"Mã dịch vụ '{unique_code}' đã tồn tại" in r2.json()["detail"]


def test_create_service_duplicate_name(client: TestClient, db: Session) -> None:
    """Tạo dịch vụ với tên dịch vụ đã tồn tại -> 409 Conflict."""
    admin = create_role_user(db, UserRole.ADMIN.value)
    headers = get_auth_headers(admin)

    unique_name = f"Tên Dịch Vụ Duy Nhất {uuid.uuid4().hex[:6]}"

    # Lần 1: Thành công
    r1 = client.post(
        "/api/services",
        headers=headers,
        json={
            "code": f"SVC-NAME1-{uuid.uuid4().hex[:4].upper()}",
            "name": unique_name,
            "base_price": 200_000,
            "estimated_duration_minutes": 30,
        },
    )
    assert r1.status_code == 201

    # Lần 2: Trùng tên -> 409 Conflict
    r2 = client.post(
        "/api/services",
        headers=headers,
        json={
            "code": f"SVC-NAME2-{uuid.uuid4().hex[:4].upper()}",
            "name": unique_name,
            "base_price": 250_000,
            "estimated_duration_minutes": 45,
        },
    )
    assert r2.status_code == 409
    assert f"Tên dịch vụ '{unique_name}' đã tồn tại" in r2.json()["detail"]


def test_admin_update_service_success(client: TestClient, db: Session) -> None:
    """Admin cập nhật thông tin dịch vụ thành công qua PUT và PATCH (200 OK)."""
    admin = create_role_user(db, UserRole.ADMIN.value)
    headers = get_auth_headers(admin)

    svc_code = f"SVC-UPD-{uuid.uuid4().hex[:6].upper()}"
    init_name = f"Dịch vụ ban đầu {uuid.uuid4().hex[:4]}"

    svc = Service(
        id=uuid.uuid4(),
        code=svc_code,
        name=init_name,
        base_price=300_000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    db.add(svc)
    db.commit()

    new_name = f"Dịch vụ sau cập nhật {uuid.uuid4().hex[:4]}"
    update_payload = {
        "name": new_name,
        "base_price": 450_000.0,
        "estimated_duration_minutes": 50,
        "description": "Mô tả mới sau khi cập nhật",
    }

    # Test qua PUT
    r = client.put(f"/api/services/{svc.id}", headers=headers, json=update_payload)
    assert r.status_code == 200
    res = r.json()
    assert res["name"] == new_name
    assert res["base_price"] == 450_000.0
    assert res["estimated_duration_minutes"] == 50
    assert res["code"] == svc_code  # Giữ nguyên mã code

    # Test qua PATCH
    patch_payload = {"base_price": 500_000.0}
    r_patch = client.patch(
        f"/api/services/{svc.id}", headers=headers, json=patch_payload
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["base_price"] == 500_000.0


def test_admin_update_service_cannot_change_code(
    client: TestClient, db: Session
) -> None:
    """Không tự ý thay đổi mã định danh (code) của dịch vụ khi cập nhật."""
    admin = create_role_user(db, UserRole.ADMIN.value)
    headers = get_auth_headers(admin)

    orig_code = f"SVC-FIXED-{uuid.uuid4().hex[:6].upper()}"
    svc = Service(
        id=uuid.uuid4(),
        code=orig_code,
        name=f"Dịch vụ giữ mã {uuid.uuid4().hex[:4]}",
        base_price=200_000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    db.add(svc)
    db.commit()

    # Cố gắng thay đổi code sang mã khác
    r = client.patch(
        f"/api/services/{svc.id}",
        headers=headers,
        json={"code": "SVC-HACKED-999", "base_price": 250_000.0},
    )
    assert r.status_code == 200
    res = r.json()
    assert res["code"] == orig_code  # Code không bị thay đổi!

    db.refresh(svc)
    assert svc.code == orig_code


def test_update_service_not_found(client: TestClient, db: Session) -> None:
    """Cập nhật dịch vụ không tồn tại -> 404 Not Found."""
    admin = create_role_user(db, UserRole.ADMIN.value)
    headers = get_auth_headers(admin)

    fake_id = uuid.uuid4()
    r = client.put(
        f"/api/services/{fake_id}",
        headers=headers,
        json={"name": "Tên mới", "base_price": 100_000},
    )
    assert r.status_code == 404
    assert "Không tìm thấy dịch vụ" in r.json()["detail"]


def test_update_service_invalid_data(client: TestClient, db: Session) -> None:
    """Cập nhật dịch vụ với dữ liệu không hợp lệ -> 422 Unprocessable Entity."""
    admin = create_role_user(db, UserRole.ADMIN.value)
    headers = get_auth_headers(admin)

    svc = Service(
        id=uuid.uuid4(),
        code=f"SVC-INV-{uuid.uuid4().hex[:4].upper()}",
        name=f"Dịch vụ kiểm tra lỗi {uuid.uuid4().hex[:4]}",
        base_price=200_000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    db.add(svc)
    db.commit()

    # Cập nhật giá âm
    r1 = client.patch(
        f"/api/services/{svc.id}", headers=headers, json={"base_price": -10}
    )
    assert r1.status_code == 422

    # Cập nhật thời gian = 0
    r2 = client.patch(
        f"/api/services/{svc.id}",
        headers=headers,
        json={"estimated_duration_minutes": 0},
    )
    assert r2.status_code == 422

    # Cập nhật tên rỗng
    r3 = client.patch(f"/api/services/{svc.id}", headers=headers, json={"name": "   "})
    assert r3.status_code == 422


def test_admin_hide_service_success(client: TestClient, db: Session) -> None:
    """
    Admin ẩn dịch vụ thành công (Soft Delete / Ngừng kinh doanh):
    - is_active chuyển thành False.
    - Dữ liệu không bị xóa khỏi database.
    """
    admin = create_role_user(db, UserRole.ADMIN.value)
    headers = get_auth_headers(admin)

    svc = Service(
        id=uuid.uuid4(),
        code=f"SVC-HIDE-{uuid.uuid4().hex[:6].upper()}",
        name=f"Dịch vụ sẽ bị ẩn {uuid.uuid4().hex[:4]}",
        base_price=350_000.0,
        estimated_duration_minutes=45,
        is_active=True,
    )
    db.add(svc)
    db.commit()

    # Gọi API ẩn dịch vụ qua PATCH /hide
    r = client.patch(f"/api/services/{svc.id}/hide", headers=headers)
    assert r.status_code == 200
    res = r.json()
    assert res["id"] == str(svc.id)
    assert res["is_active"] is False

    # Xác nhận trong database vẫn tồn tại nhưng is_active == False
    db.refresh(svc)
    assert svc is not None
    assert svc.is_active is False

    # Cũng hỗ trợ POST /hide
    r_post = client.post(f"/api/services/{svc.id}/hide", headers=headers)
    assert r_post.status_code == 200
    assert r_post.json()["is_active"] is False


def test_hide_service_not_found(client: TestClient, db: Session) -> None:
    """Ẩn dịch vụ không tồn tại -> 404 Not Found."""
    admin = create_role_user(db, UserRole.ADMIN.value)
    headers = get_auth_headers(admin)

    fake_id = uuid.uuid4()
    r = client.patch(f"/api/services/{fake_id}/hide", headers=headers)
    assert r.status_code == 404
    assert "Không tìm thấy dịch vụ" in r.json()["detail"]


def test_unauthenticated_user_cannot_access_management_apis(
    client: TestClient, db: Session
) -> None:
    """Người dùng chưa đăng nhập gọi API quản trị -> 401 Unauthorized."""
    svc = Service(
        id=uuid.uuid4(),
        code=f"SVC-UNAUTH-{uuid.uuid4().hex[:4].upper()}",
        name=f"Dịch vụ unauth {uuid.uuid4().hex[:4]}",
        base_price=200_000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    db.add(svc)
    db.commit()

    # 1. Tạo dịch vụ không token
    r_create = client.post(
        "/api/services",
        json={"code": "SVC-NOAUTH", "name": "No auth", "base_price": 100_000},
    )
    assert r_create.status_code == 401

    # 2. Cập nhật dịch vụ không token
    r_update = client.put(f"/api/services/{svc.id}", json={"name": "Updated No Auth"})
    assert r_update.status_code == 401

    # 3. Ẩn dịch vụ không token
    r_hide = client.patch(f"/api/services/{svc.id}/hide")
    assert r_hide.status_code == 401


def test_customer_forbidden_from_management_apis(
    client: TestClient, db: Session
) -> None:
    """Khách hàng đăng nhập nhưng không có quyền quản trị gọi API -> 403 Forbidden."""
    cust = create_role_user(db, UserRole.CUSTOMER.value)
    headers = get_auth_headers(cust)

    svc = Service(
        id=uuid.uuid4(),
        code=f"SVC-FORBID-{uuid.uuid4().hex[:4].upper()}",
        name=f"Dịch vụ forbid {uuid.uuid4().hex[:4]}",
        base_price=200_000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    db.add(svc)
    db.commit()

    # 1. Khách hàng cố tạo dịch vụ -> 403
    r_create = client.post(
        "/api/services",
        headers=headers,
        json={"code": "SVC-CUST-TRY", "name": "Cust Try", "base_price": 100_000},
    )
    assert r_create.status_code == 403

    # 2. Khách hàng cố sửa dịch vụ -> 403
    r_update = client.put(
        f"/api/services/{svc.id}",
        headers=headers,
        json={"name": "Cust update attempt"},
    )
    assert r_update.status_code == 403

    # 3. Khách hàng cố ẩn dịch vụ -> 403
    r_hide = client.patch(f"/api/services/{svc.id}/hide", headers=headers)
    assert r_hide.status_code == 403


def test_hidden_service_not_in_customer_list(client: TestClient, db: Session) -> None:
    """
    Kiểm tra dịch vụ đã ẩn không còn xuất hiện trong danh sách dịch vụ dành cho khách hàng:
    - Khách hàng gọi GET /api/services -> Chỉ thấy dịch vụ is_active=True.
    - Quản trị viên gọi GET /api/services?include_inactive=true -> Thấy cả dịch vụ ẩn.
    """
    suffix = uuid.uuid4().hex[:6].upper()
    active_code = f"SVC-ACT-{suffix}"
    hidden_code = f"SVC-HID-{suffix}"

    active_svc = Service(
        id=uuid.uuid4(),
        code=active_code,
        name=f"Dịch vụ đang kinh doanh {suffix}",
        base_price=300_000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    hidden_svc = Service(
        id=uuid.uuid4(),
        code=hidden_code,
        name=f"Dịch vụ ngừng kinh doanh {suffix}",
        base_price=300_000.0,
        estimated_duration_minutes=30,
        is_active=False,
    )
    db.add(active_svc)
    db.add(hidden_svc)
    db.commit()

    # Khách hàng gọi lấy danh sách dịch vụ
    cust = create_role_user(db, UserRole.CUSTOMER.value)
    cust_headers = get_auth_headers(cust)

    r_cust = client.get("/api/services", headers=cust_headers)
    assert r_cust.status_code == 200
    cust_services = r_cust.json()["data"]
    returned_codes = [s["code"] for s in cust_services]

    assert active_code in returned_codes
    assert hidden_code not in returned_codes  # Dịch vụ ẩn KHÔNG xuất hiện

    # Quản trị viên gọi với include_inactive=true -> Thấy dịch vụ ẩn
    admin = create_role_user(db, UserRole.ADMIN.value)
    admin_headers = get_auth_headers(admin)

    r_admin = client.get(
        f"/api/services?include_inactive=true&q={suffix}", headers=admin_headers
    )
    assert r_admin.status_code == 200
    admin_codes = [s["code"] for s in r_admin.json()["data"]]
    assert active_code in admin_codes
    assert hidden_code in admin_codes


def test_hidden_service_preserves_appointment_history_reference(
    client: TestClient, db: Session
) -> None:
    """
    Kiểm tra lịch sử đặt lịch cũ vẫn tham chiếu được dịch vụ đã ẩn:
    - Dịch vụ được liên kết với lịch hẹn trong AppointmentService.
    - Sau khi ẩn dịch vụ (is_active=False), bản ghi lịch hẹn và quan hệ AppointmentService vẫn nguyên vẹn.
    """
    admin = create_role_user(db, UserRole.ADMIN.value)
    admin_headers = get_auth_headers(admin)

    cust_user = create_role_user(db, UserRole.CUSTOMER.value)
    customer = Customer(
        full_name="Khách Hàng Đặt Lịch Cũ",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
        user_id=cust_user.id,
    )
    device = Device(customer_id=customer.id, brand="Apple", model="iPhone X")
    tech = Technician(
        full_name="Kỹ Thuật Viên Test Lịch Sử",
        phone_number=f"092{uuid.uuid4().int % 10000000:07d}",
        is_active=True,
    )

    svc_code = f"SVC-APPT-{uuid.uuid4().hex[:6].upper()}"
    svc = Service(
        id=uuid.uuid4(),
        code=svc_code,
        name=f"Dịch Vụ Có Lịch Hẹn {uuid.uuid4().hex[:4]}",
        base_price=500_000.0,
        estimated_duration_minutes=45,
        is_active=True,
    )
    db.add(customer)
    db.add(device)
    db.add(tech)
    db.add(svc)
    db.commit()

    # Tạo lịch hẹn trong quá khứ liên kết với dịch vụ này
    appt = Appointment(
        appointment_number=f"APPT-TEST-{uuid.uuid4().hex[:6].upper()}",
        customer_id=customer.id,
        device_id=device.id,
        technician_id=tech.id,
        appointment_date=datetime.now(UTC) - timedelta(days=10),
        status="COMPLETED",
        total_amount=500_000.0,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    appt_svc = AppointmentService(
        appointment_id=appt.id,
        service_id=svc.id,
        price_at_booking=500_000.0,
        quantity=1,
    )
    db.add(appt_svc)
    db.commit()

    # Bây giờ Admin thực hiện ẩn dịch vụ
    r_hide = client.patch(f"/api/services/{svc.id}/hide", headers=admin_headers)
    assert r_hide.status_code == 200
    assert r_hide.json()["is_active"] is False

    # Kiểm tra liên kết giữa AppointmentService và Service đã ẩn vẫn hoàn toàn nguyên vẹn
    linked_appts = db.exec(
        select(AppointmentService).where(AppointmentService.service_id == svc.id)
    ).all()
    assert len(linked_appts) == 1
    assert linked_appts[0].appointment_id == appt.id
    assert linked_appts[0].price_at_booking == 500_000.0

    # Lấy Service từ relationship của AppointmentService sau khi reload
    db.expire_all()
    referenced_svc = db.get(Service, linked_appts[0].service_id)
    assert referenced_svc is not None
    assert referenced_svc.id == svc.id
    assert referenced_svc.code == svc_code
    assert referenced_svc.is_active is False  # Đã ẩn nhưng vẫn bảo toàn lịch sử


def test_manager_role_can_manage_services(client: TestClient, db: Session) -> None:
    """Tài khoản có vai trò Manager cũng có toàn quyền quản trị danh mục dịch vụ."""
    mgr = create_role_user(db, UserRole.MANAGER.value)
    headers = get_auth_headers(mgr)

    code = f"SVC-MGR-{uuid.uuid4().hex[:6].upper()}"
    name = f"Dịch vụ do Manager tạo {uuid.uuid4().hex[:4]}"

    # 1. Manager tạo dịch vụ
    r_create = client.post(
        "/api/services",
        headers=headers,
        json={
            "code": code,
            "name": name,
            "base_price": 180_000,
            "estimated_duration_minutes": 25,
        },
    )
    assert r_create.status_code == 201
    svc_id = r_create.json()["id"]

    # 2. Manager sửa dịch vụ
    r_update = client.patch(
        f"/api/services/{svc_id}",
        headers=headers,
        json={"base_price": 220_000},
    )
    assert r_update.status_code == 200
    assert r_update.json()["base_price"] == 220_000.0

    # 3. Manager ẩn dịch vụ
    r_hide = client.patch(f"/api/services/{svc_id}/hide", headers=headers)
    assert r_hide.status_code == 200
    assert r_hide.json()["is_active"] is False
