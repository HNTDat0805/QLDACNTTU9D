import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import security
from app.crud import create_user
from app.models import (
    Appointment,
    AppointmentService,
    AppointmentStatus,
    Customer,
    Device,
    RepairStatusHistory,
    Service,
    Technician,
    User,
    UserCreate,
)
from tests.utils.utils import random_email


def get_token_headers(user: User) -> dict[str, str]:
    token = security.create_access_token(
        subject=user.id, role=user.role, email=user.email
    )
    return {"Authorization": f"Bearer {token}"}


def create_role_user(db: Session, role: str) -> User:
    email = random_email()
    user_in = UserCreate(
        email=email,
        password="testPassword123",
        full_name=f"Test {role.title()}",
        role=role,
    )
    return create_user(session=db, user_create=user_in)


def setup_intake_fixture(db: Session) -> dict[str, object]:
    cust = Customer(
        full_name="Nguyễn Văn A",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
        email=random_email(),
        address="123 Đường Cầu Giấy, Hà Nội",
    )
    db.add(cust)
    db.commit()

    device = Device(
        customer_id=cust.id,
        brand="Apple",
        model="iPhone 13 Pro",
        color="Sierra Blue",
        imei=f"356{uuid.uuid4().int % 1000000000000:012d}",
        serial_number=f"F2L{uuid.uuid4().hex[:8].upper()}",
    )
    db.add(device)

    tech = Technician(
        full_name="Kỹ Thuật Viên Tuấn",
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
        specialization="Sửa chữa phần cứng",
        is_active=True,
    )
    db.add(tech)

    inactive_tech = Technician(
        full_name="Kỹ Thuật Viên Đã Nghỉ",
        phone_number=f"097{uuid.uuid4().int % 10000000:07d}",
        is_active=False,
    )
    db.add(inactive_tech)

    svc = Service(
        name=f"Thay Pin Dung Lượng Cao {uuid.uuid4().hex[:4]}",
        base_price=650_000.0,
        estimated_duration_minutes=45,
        is_active=True,
    )
    db.add(svc)
    db.commit()

    appt = Appointment(
        appointment_number=f"APPT-20261024-{uuid.uuid4().hex[:4].upper()}",
        appointment_date=datetime.now(UTC),
        status=AppointmentStatus.PENDING.value,
        customer_id=cust.id,
        device_id=device.id,
        technician_id=tech.id,
        customer_notes="Máy bị phồng pin, hao nguồn nhanh",
        technician_diagnosis=None,
        total_amount=svc.base_price,
    )
    db.add(appt)
    db.commit()

    appt_svc = AppointmentService(
        appointment_id=appt.id,
        service_id=svc.id,
        price_at_booking=svc.base_price,
        quantity=1,
    )
    db.add(appt_svc)
    db.commit()

    return {
        "customer": cust,
        "device": device,
        "technician": tech,
        "inactive_technician": inactive_tech,
        "service": svc,
        "appointment": appt,
    }


def test_create_intake_from_existing_appointment_success(
    client: TestClient, db: Session
) -> None:
    """Test tiếp nhận thiết bị từ một lịch hẹn có sẵn thành công."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_intake_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    payload = {
        "appointment_id": str(appt.id),
        "physical_condition": "Màn hình trầy nhẹ góc dưới, sườn máy có vết cấn nhỏ",
        "fault_description": "Khách báo pin chai 72%, sạc không vào đầy 100%",
        "accessories_received": "Cáp sạc Type-C, ốp lưng màu đen",
        "initial_status": "CONFIRMED",
    }

    response = client.post("/api/v1/intake", json=payload, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "Tạo phiếu tiếp nhận thiết bị thành công" in body["message"]

    data = body["data"]
    assert data["id"] == str(appt.id)
    assert data["status"] == "CONFIRMED"
    assert "Màn hình trầy nhẹ" in data["physical_condition"]
    assert "Khách báo pin chai" in data["fault_description"]
    assert data["accessories_received"] == "Cáp sạc Type-C, ốp lưng màu đen"
    assert data["appointment_number"] == appt.appointment_number

    # Làm mới session để nạp dữ liệu đã commit từ API
    db.expire_all()

    # Kiểm tra database cập nhật và ghi RepairStatusHistory
    db_appt = db.get(Appointment, appt.id)
    assert db_appt is not None
    assert db_appt.status == "CONFIRMED"
    assert "Màn hình trầy nhẹ" in (db_appt.technician_diagnosis or "")

    history = db.exec(
        select(RepairStatusHistory).where(RepairStatusHistory.appointment_id == appt.id)
    ).all()
    assert len(history) >= 1
    latest_hist = history[-1]
    assert latest_hist.previous_status == "PENDING"
    assert latest_hist.new_status == "CONFIRMED"
    assert latest_hist.changed_by_user_id == staff.id
    assert "Tiếp nhận thiết bị sửa chữa" in (latest_hist.note or "")


def test_create_intake_walkin_success(client: TestClient, db: Session) -> None:
    """Test tạo phiếu tiếp nhận thiết bị trực tiếp tại quầy cho khách vãng lai."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_intake_fixture(db)
    svc = fix["service"]
    tech = fix["technician"]
    assert isinstance(svc, Service)
    assert isinstance(tech, Technician)

    phone = f"093{uuid.uuid4().int % 10000000:07d}"
    imei = f"861{uuid.uuid4().int % 1000000000000:012d}"
    payload = {
        "customer_name": "Trần Thị Bích",
        "customer_phone": phone,
        "customer_email": "bich.tran@example.com",
        "customer_address": "456 Kim Mã, Ba Đình, Hà Nội",
        "brand": "Samsung",
        "model": "Galaxy S22 Ultra",
        "color": "Phantom Black",
        "imei": imei,
        "physical_condition": "Màn hình nứt kính góc trên bên phải, lưng nguyên vẹn",
        "fault_description": "Màn hình chớp tắt liên tục khi bật sáng",
        "accessories_received": "Hộp máy, cáp sạc nhanh Samsung",
        "technician_id": str(tech.id),
        "service_ids": [str(svc.id)],
        "initial_status": "IN_PROGRESS",
    }

    response = client.post("/api/v1/intake", json=payload, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True

    data = body["data"]
    assert data["customer_name"] == "Trần Thị Bích"
    assert data["customer_phone"] == phone
    assert data["device_brand"] == "Samsung"
    assert data["device_model"] == "Galaxy S22 Ultra"
    assert data["device_imei"] == imei
    assert data["status"] == "IN_PROGRESS"
    assert data["total_amount"] == svc.base_price
    assert len(data["services"]) == 1
    assert data["services"][0]["service_id"] == str(svc.id)
    assert data["technician_name"] == tech.full_name

    # Kiểm tra database tạo mới các thực thể đúng đắn
    created_cust = db.exec(
        select(Customer).where(Customer.phone_number == phone)
    ).first()
    assert created_cust is not None
    assert created_cust.full_name == "Trần Thị Bích"

    created_device = db.exec(
        select(Device).where(Device.customer_id == created_cust.id)
    ).first()
    assert created_device is not None
    assert created_device.brand == "Samsung"
    assert created_device.imei == imei

    created_appt = db.get(Appointment, uuid.UUID(data["id"]))
    assert created_appt is not None
    assert created_appt.status == "IN_PROGRESS"

    history = db.exec(
        select(RepairStatusHistory).where(
            RepairStatusHistory.appointment_id == created_appt.id
        )
    ).all()
    assert len(history) >= 1
    assert history[0].previous_status is None
    assert history[0].new_status == "IN_PROGRESS"
    assert history[0].changed_by_user_id == staff.id


def test_create_intake_walkin_reuse_existing_customer(
    client: TestClient, db: Session
) -> None:
    """Test tiếp nhận walk-in tự động nhận diện và tái sử dụng khách hàng đã có theo số điện thoại."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_intake_fixture(db)
    cust = fix["customer"]
    assert isinstance(cust, Customer)

    payload = {
        "customer_name": "Tên Khác Nhưng Cùng Số Điện Thoại",
        "customer_phone": cust.phone_number,
        "brand": "Xiaomi",
        "model": "Redmi Note 11",
        "physical_condition": "Vỏ móp góc, máy hoạt động bình thường",
        "fault_description": "Hỏng loa trong, gọi điện không nghe thấy gì",
        "initial_status": "CONFIRMED",
    }

    response = client.post("/api/v1/intake", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()["data"]
    # Customer ID phải là customer đã có
    assert data["customer_id"] == str(cust.id)


def test_create_intake_missing_required_fields_validation_error(
    client: TestClient, db: Session
) -> None:
    """Test validation Pydantic bắt lỗi khi thiếu các trường bắt buộc."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)

    # 1. Trống physical_condition
    payload1 = {
        "customer_name": "Lê Văn C",
        "customer_phone": "0912345678",
        "brand": "Apple",
        "model": "iPhone 11",
        "physical_condition": "   ",
        "fault_description": "Hỏng màn hình",
    }
    res1 = client.post("/api/v1/intake", json=payload1, headers=headers)
    assert res1.status_code == 422

    # 2. Trống fault_description
    payload2 = {
        "customer_name": "Lê Văn C",
        "customer_phone": "0912345678",
        "brand": "Apple",
        "model": "iPhone 11",
        "physical_condition": "Ngoại quan tốt",
        "fault_description": "   ",
    }
    res2 = client.post("/api/v1/intake", json=payload2, headers=headers)
    assert res2.status_code == 422

    # 3. Không có appointment_id và thiếu customer info
    payload3 = {
        "brand": "Apple",
        "model": "iPhone 11",
        "physical_condition": "Ngoại quan tốt",
        "fault_description": "Hỏng màn hình",
    }
    res3 = client.post("/api/v1/intake", json=payload3, headers=headers)
    assert res3.status_code == 422

    # 4. Không có appointment_id và thiếu device info
    payload4 = {
        "customer_name": "Lê Văn C",
        "customer_phone": "0912345678",
        "physical_condition": "Ngoại quan tốt",
        "fault_description": "Hỏng màn hình",
    }
    res4 = client.post("/api/v1/intake", json=payload4, headers=headers)
    assert res4.status_code == 422

    # 5. initial_status không hợp lệ (không được là CANCELLED hoặc COMPLETED khi lập phiếu)
    payload5 = {
        "customer_name": "Lê Văn C",
        "customer_phone": "0912345678",
        "brand": "Apple",
        "model": "iPhone 11",
        "physical_condition": "Ngoại quan tốt",
        "fault_description": "Hỏng màn hình",
        "initial_status": "CANCELLED",
    }
    res5 = client.post("/api/v1/intake", json=payload5, headers=headers)
    assert res5.status_code == 422


def test_create_intake_not_found_references(client: TestClient, db: Session) -> None:
    """Test trả về 404 khi tham chiếu đến appointment/customer/device/service không tồn tại."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    random_id = uuid.uuid4()

    # 1. Appointment không tồn tại
    payload1 = {
        "appointment_id": str(random_id),
        "physical_condition": "Vỏ xước nhẹ",
        "fault_description": "Lỗi cảm biến vân tay",
    }
    res1 = client.post("/api/v1/intake", json=payload1, headers=headers)
    assert res1.status_code == 404
    assert "Không tìm thấy lịch hẹn" in res1.json()["detail"]

    # 2. Customer ID chỉ định không tồn tại
    payload2 = {
        "customer_id": str(random_id),
        "brand": "Oppo",
        "model": "Reno 8",
        "physical_condition": "Vỏ xước nhẹ",
        "fault_description": "Lỗi cảm biến vân tay",
    }
    res2 = client.post("/api/v1/intake", json=payload2, headers=headers)
    assert res2.status_code == 404
    assert "Không tìm thấy khách hàng" in res2.json()["detail"]

    # 3. Device ID chỉ định không tồn tại
    fix = setup_intake_fixture(db)
    cust = fix["customer"]
    assert isinstance(cust, Customer)
    payload3 = {
        "customer_id": str(cust.id),
        "device_id": str(random_id),
        "physical_condition": "Vỏ xước nhẹ",
        "fault_description": "Lỗi sạc",
    }
    res3 = client.post("/api/v1/intake", json=payload3, headers=headers)
    assert res3.status_code == 404
    assert "Không tìm thấy thiết bị" in res3.json()["detail"]

    # 4. Service ID không tồn tại
    payload4 = {
        "customer_name": "Phan Anh",
        "customer_phone": "0987654321",
        "brand": "Vivo",
        "model": "V25",
        "physical_condition": "Bình thường",
        "fault_description": "Chân sạc lỏng",
        "service_ids": [str(random_id)],
    }
    res4 = client.post("/api/v1/intake", json=payload4, headers=headers)
    assert res4.status_code == 404
    assert "Không tìm thấy dịch vụ" in res4.json()["detail"]


def test_create_intake_conflict_and_duplicate_rules(
    client: TestClient, db: Session
) -> None:
    """Test các quy tắc chống trùng lặp và xung đột (409 Conflict)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_intake_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    # 1. Lịch hẹn đã bị CANCELLED
    appt.status = AppointmentStatus.CANCELLED.value
    db.add(appt)
    db.commit()

    payload = {
        "appointment_id": str(appt.id),
        "physical_condition": "Máy vỡ kính",
        "fault_description": "Mất nguồn",
    }
    res1 = client.post("/api/v1/intake", json=payload, headers=headers)
    assert res1.status_code == 409
    assert "Lịch hẹn đã bị hủy" in res1.json()["detail"]

    # 2. Lịch hẹn đã COMPLETED
    appt.status = AppointmentStatus.COMPLETED.value
    db.add(appt)
    db.commit()
    res2 = client.post("/api/v1/intake", json=payload, headers=headers)
    assert res2.status_code == 409
    assert "Lịch hẹn đã hoàn tất" in res2.json()["detail"]

    # 3. Lịch hẹn đã ở trạng thái IN_PROGRESS (đã tiếp nhận trước đó)
    appt.status = AppointmentStatus.IN_PROGRESS.value
    db.add(appt)
    db.commit()
    res3 = client.post("/api/v1/intake", json=payload, headers=headers)
    assert res3.status_code == 409
    assert "đã được tiếp nhận và đang trong quá trình sửa chữa" in res3.json()["detail"]

    # 4. Trùng thiết bị có IMEI đang sửa dở dang
    dev = fix["device"]
    assert isinstance(dev, Device)
    assert dev.imei is not None

    payload_dup = {
        "customer_name": "Khách Vãng Lai Trùng IMEI",
        "customer_phone": f"096{uuid.uuid4().int % 10000000:07d}",
        "brand": "Apple",
        "model": "iPhone 13 Pro",
        "imei": dev.imei,
        "physical_condition": "Máy cấn góc",
        "fault_description": "Thay pin",
    }
    res4 = client.post("/api/v1/intake", json=payload_dup, headers=headers)
    assert res4.status_code == 409
    assert "đang có phiếu sửa chữa dở dang" in res4.json()["detail"]


def test_create_intake_inactive_technician_bad_request(
    client: TestClient, db: Session
) -> None:
    """Test trả về 400 Bad Request khi gán kỹ thuật viên không còn hoạt động."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_intake_fixture(db)
    inactive_tech = fix["inactive_technician"]
    assert isinstance(inactive_tech, Technician)

    payload = {
        "customer_name": "Vũ Mạnh Hùng",
        "customer_phone": "0945678910",
        "brand": "Google",
        "model": "Pixel 7 Pro",
        "physical_condition": "Đẹp như mới",
        "fault_description": "Mất sóng 4G",
        "technician_id": str(inactive_tech.id),
    }
    response = client.post("/api/v1/intake", json=payload, headers=headers)
    assert response.status_code == 400
    assert "Kỹ thuật viên này hiện không còn hoạt động" in response.json()["detail"]


def test_create_intake_rbac_permissions(client: TestClient, db: Session) -> None:
    """Test phân quyền: Chỉ Staff/Manager/Admin được tạo phiếu tiếp nhận, Customer bị cấm (403)."""
    customer_user = create_role_user(db, "customer")
    cust_headers = get_token_headers(customer_user)

    payload = {
        "customer_name": "Khách Tự Tiếp Nhận",
        "customer_phone": "0911223344",
        "brand": "Apple",
        "model": "iPhone 12",
        "physical_condition": "Tốt",
        "fault_description": "Hỏng loa",
    }

    # 1. Khách hàng thông thường gọi API -> 403 Forbidden
    res1 = client.post("/api/v1/intake", json=payload, headers=cust_headers)
    assert res1.status_code == 403

    # 2. Không truyền token -> 401 Unauthorized
    res2 = client.post("/api/v1/intake", json=payload)
    assert res2.status_code == 401

    # 3. Manager gọi API -> 201 Thành công
    manager_user = create_role_user(db, "manager")
    mgr_headers = get_token_headers(manager_user)
    res3 = client.post("/api/v1/intake", json=payload, headers=mgr_headers)
    assert res3.status_code == 201


def test_create_intake_database_error_transaction_rollback(
    client: TestClient, db: Session
) -> None:
    """Test xử lý lỗi ngoại lệ database: session được rollback an toàn và trả về 500 an toàn."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)

    payload = {
        "customer_name": "Lỗi Database Rollback",
        "customer_phone": "0900998877",
        "brand": "Sony",
        "model": "Xperia 1",
        "physical_condition": "Trầy xước",
        "fault_description": "Không khởi động được",
    }

    # Mock slot_service.generate_appointment_code để sinh lỗi Runtime bất ngờ
    with patch(
        "app.services.intake_service.slot_service.generate_appointment_code",
        side_effect=RuntimeError("Simulated database failure"),
    ):
        response = client.post("/api/v1/intake", json=payload, headers=headers)
        assert response.status_code == 500
        assert (
            "Đã xảy ra lỗi trong quá trình tạo phiếu tiếp nhận thiết bị"
            in (response.json()["detail"])
        )

    # Đảm bảo không tạo dữ liệu dở dang (customer này không được commit)
    leftover_cust = db.exec(
        select(Customer).where(Customer.phone_number == "0900998877")
    ).first()
    assert leftover_cust is None
