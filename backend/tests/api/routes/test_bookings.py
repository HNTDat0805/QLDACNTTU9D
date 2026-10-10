import uuid
from datetime import date, time, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import (
    Appointment,
    AppointmentService,
    Customer,
    Device,
    RepairStatusHistory,
    Service,
    Technician,
    TechnicianSchedule,
    User,
)
from tests.utils.user import authentication_token_from_email


@pytest.fixture
def booking_test_env(db: Session) -> dict[str, object]:
    """Setup clean isolated test customer, device, technician, schedule and services."""
    # 1. Customer User A
    user_a = User(
        email=f"cust_a_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashedpassword123",
        role="customer",
        is_active=True,
    )
    # 2. Customer User B
    user_b = User(
        email=f"cust_b_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashedpassword123",
        role="customer",
        is_active=True,
    )
    # 3. Staff User
    user_staff = User(
        email=f"staff_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashedpassword123",
        role="staff",
        is_active=True,
    )
    db.add(user_a)
    db.add(user_b)
    db.add(user_staff)
    db.flush()

    # Customer profiles
    cust_a = Customer(
        full_name="Nguyễn Văn A",
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
        user_id=user_a.id,
    )
    cust_b = Customer(
        full_name="Trần Thị B",
        phone_number=f"097{uuid.uuid4().int % 10000000:07d}",
        user_id=user_b.id,
    )
    db.add(cust_a)
    db.add(cust_b)
    db.flush()

    # Devices
    dev_a = Device(
        customer_id=cust_a.id,
        device_type="Smartphone",
        brand="Apple",
        model="iPhone 14",
    )
    dev_b = Device(
        customer_id=cust_b.id,
        device_type="Smartphone",
        brand="Samsung",
        model="Galaxy S23",
    )
    db.add(dev_a)
    db.add(dev_b)
    db.flush()

    # Technicians
    tech1 = Technician(
        full_name="Nguyễn Kỹ Thuật 1",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
        specialization="Màn hình",
        is_active=True,
    )
    tech2 = Technician(
        full_name="Trần Kỹ Thuật 2",
        phone_number=f"092{uuid.uuid4().int % 10000000:07d}",
        specialization="Pin & Nguồn",
        is_active=True,
    )
    db.add(tech1)
    db.add(tech2)
    db.flush()

    # Working schedule for 10 days in future
    target_date = date.today() + timedelta(days=10)
    sched1 = TechnicianSchedule(
        technician_id=tech1.id,
        work_date=target_date,
        start_time=time(8, 0),
        end_time=time(18, 0),
        status="AVAILABLE",
    )
    sched2 = TechnicianSchedule(
        technician_id=tech2.id,
        work_date=target_date,
        start_time=time(8, 0),
        end_time=time(18, 0),
        status="AVAILABLE",
    )
    db.add(sched1)
    db.add(sched2)

    # Services
    svc_screen = Service(
        name=f"Thay màn hình OLED {uuid.uuid4().hex[:4]}",
        base_price=1_500_000.0,
        estimated_duration_minutes=60,
        is_active=True,
    )
    svc_battery = Service(
        name=f"Thay pin dung lượng cao {uuid.uuid4().hex[:4]}",
        base_price=450_000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    svc_inactive = Service(
        name=f"Dịch vụ ngừng hỗ trợ {uuid.uuid4().hex[:4]}",
        base_price=100_000.0,
        estimated_duration_minutes=30,
        is_active=False,
    )
    db.add(svc_screen)
    db.add(svc_battery)
    db.add(svc_inactive)
    db.commit()

    return {
        "user_a": user_a,
        "user_b": user_b,
        "user_staff": user_staff,
        "customer_a": cust_a,
        "customer_b": cust_b,
        "device_a": dev_a,
        "device_b": dev_b,
        "tech1": tech1,
        "tech2": tech2,
        "target_date": target_date,
        "svc_screen": svc_screen,
        "svc_battery": svc_battery,
        "svc_inactive": svc_inactive,
    }


# ============================================================================
# API 1: CREATE BOOKING TESTS (POST /api/bookings)
# ============================================================================


def test_create_booking_success(
    client: TestClient,
    booking_test_env: dict[str, object],
    db: Session,
) -> None:
    """1. Tạo đặt chỗ thành công với đầy đủ thông tin hợp lệ qua /api/bookings."""
    cust_a = booking_test_env["customer_a"]
    dev_a = booking_test_env["device_a"]
    tech1 = booking_test_env["tech1"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(dev_a, Device)
    assert isinstance(tech1, Technician)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    payload = {
        "customer_id": str(cust_a.id),
        "device_id": str(dev_a.id),
        "service_id": str(svc_screen.id),
        "technician_id": str(tech1.id),
        "appointment_date": t_date.isoformat(),
        "start_time": "09:00",
        "description": "Màn hình nứt góc trên",
    }

    response = client.post("/api/bookings", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "appointment_id" in data
    assert "appointment_code" in data
    assert data["appointment_date"] == t_date.isoformat()
    assert data["start_time"] == "09:00"
    assert data["end_time"] == "10:00"
    assert data["status"] == "PENDING"
    assert data["total_amount"] == 1_500_000.0
    assert svc_screen.name in data["service_names"]

    # Verify DB state
    appt = db.get(Appointment, uuid.UUID(data["appointment_id"]))
    assert appt is not None
    assert appt.customer_id == cust_a.id
    assert appt.technician_id == tech1.id
    assert appt.status == "PENDING"

    # Verify services attached
    services = db.exec(
        select(AppointmentService).where(AppointmentService.appointment_id == appt.id)
    ).all()
    assert len(services) == 1
    assert services[0].service_id == svc_screen.id

    # Verify audit history
    histories = db.exec(
        select(RepairStatusHistory).where(RepairStatusHistory.appointment_id == appt.id)
    ).all()
    assert len(histories) == 1
    assert histories[0].new_status == "PENDING"


def test_create_booking_guest_with_contact_info(
    client: TestClient,
    booking_test_env: dict[str, object],
    db: Session,
) -> None:
    """2. Khách vãng lai đặt chỗ cung cấp số điện thoại, tên và thông tin thiết bị."""
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    guest_phone = f"093{uuid.uuid4().int % 10000000:07d}"
    payload = {
        "customer_phone": guest_phone,
        "customer_name": "Khách Vãng Lai",
        "customer_email": "guest@gmail.com",
        "customer_address": "123 Quận 1, TP.HCM",
        "device_brand": "Xiaomi",
        "device_model": "13 Pro",
        "service_id": str(svc_screen.id),
        "appointment_date": t_date.isoformat(),
        "start_time": "14:00",
        "description": "Thay kính Xiaomi",
    }

    response = client.post("/api/bookings", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"

    # Verify new customer auto-created
    created_cust = db.exec(
        select(Customer).where(Customer.phone_number == guest_phone)
    ).first()
    assert created_cust is not None
    assert created_cust.full_name == "Khách Vãng Lai"


def test_create_booking_with_multiple_services(
    client: TestClient,
    booking_test_env: dict[str, object],
    db: Session,
) -> None:
    """3. Đặt chỗ chọn nhiều dịch vụ cùng lúc (service_ids)."""
    cust_a = booking_test_env["customer_a"]
    dev_a = booking_test_env["device_a"]
    svc_screen = booking_test_env["svc_screen"]
    svc_battery = booking_test_env["svc_battery"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(dev_a, Device)
    assert isinstance(svc_screen, Service)
    assert isinstance(svc_battery, Service)
    assert isinstance(t_date, date)

    payload = {
        "customer_id": str(cust_a.id),
        "device_id": str(dev_a.id),
        "service_ids": [str(svc_screen.id), str(svc_battery.id)],
        "appointment_date": t_date.isoformat(),
        "start_time": "10:30",
        "description": "Thay cả màn hình và pin",
    }

    response = client.post("/api/bookings", json=payload)
    assert response.status_code == 201
    data = response.json()
    # 60 mins + 30 mins = 90 mins -> 10:30 to 12:00
    assert data["start_time"] == "10:30"
    assert data["end_time"] == "12:00"
    assert data["total_amount"] == 1_500_000.0 + 450_000.0
    assert len(data["service_names"]) == 2

    # Check DB
    appt_id = uuid.UUID(data["appointment_id"])
    appt_services = db.exec(
        select(AppointmentService).where(AppointmentService.appointment_id == appt_id)
    ).all()
    assert len(appt_services) == 2


def test_create_booking_missing_required_fields_422(
    client: TestClient,
    booking_test_env: dict[str, object],
) -> None:
    """4. Thiếu trường bắt buộc hoặc dữ liệu sai định dạng trả về 422 Unprocessable Entity."""
    svc_screen = booking_test_env["svc_screen"]
    cust_a = booking_test_env["customer_a"]
    t_date = booking_test_env["target_date"]
    assert isinstance(svc_screen, Service)
    assert isinstance(cust_a, Customer)
    assert isinstance(t_date, date)

    # 4a. Thiếu cả customer_id lẫn customer_phone
    res_no_cust = client.post(
        "/api/bookings",
        json={
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
        },
    )
    assert res_no_cust.status_code == 422

    # 4b. Thiếu dịch vụ
    res_no_svc = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
        },
    )
    assert res_no_svc.status_code == 422

    # 4c. Sai định dạng ngày
    res_bad_date = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_screen.id),
            "appointment_date": "sai-dinh-dang-ngay",
            "start_time": "09:00",
        },
    )
    assert res_bad_date.status_code == 422

    # 4d. Sai định dạng giờ
    res_bad_time = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "99:99",
        },
    )
    assert res_bad_time.status_code == 422


def test_create_booking_resource_not_found_404(
    client: TestClient,
    booking_test_env: dict[str, object],
) -> None:
    """5. Tham chiếu tài nguyên không tồn tại trả về 404 Not Found."""
    cust_a = booking_test_env["customer_a"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    non_existent = str(uuid.uuid4())

    # 5a. Khách hàng không tồn tại
    res_cust = client.post(
        "/api/bookings",
        json={
            "customer_id": non_existent,
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
        },
    )
    assert res_cust.status_code == 404

    # 5b. Dịch vụ không tồn tại
    res_svc = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": non_existent,
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
        },
    )
    assert res_svc.status_code == 404

    # 5c. Kỹ thuật viên không tồn tại
    res_tech = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_screen.id),
            "technician_id": non_existent,
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
        },
    )
    assert res_tech.status_code == 404


def test_create_booking_slot_conflict_409(
    client: TestClient,
    booking_test_env: dict[str, object],
) -> None:
    """6. Đặt trùng khung giờ kỹ thuật viên đã kín lịch trả về 409 Conflict."""
    cust_a = booking_test_env["customer_a"]
    cust_b = booking_test_env["customer_b"]
    tech1 = booking_test_env["tech1"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(cust_b, Customer)
    assert isinstance(tech1, Technician)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    # Request 1: 08:00 -> 09:00 cho tech1
    res1 = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "technician_id": str(tech1.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "08:00",
        },
    )
    assert res1.status_code == 201

    # Request 2: Cố tình đặt cùng tech1 vào 08:00
    res2 = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_b.id),
            "technician_id": str(tech1.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "08:00",
        },
    )
    assert res2.status_code == 409
    assert "đã có lịch hẹn" in res2.json()["detail"].lower()


def test_create_booking_outside_working_schedule_400(
    client: TestClient,
    booking_test_env: dict[str, object],
) -> None:
    """7. Đặt vào ngày kỹ thuật viên không có ca làm việc trả về 400 Bad Request."""
    cust_a = booking_test_env["customer_a"]
    tech1 = booking_test_env["tech1"]
    svc_screen = booking_test_env["svc_screen"]
    assert isinstance(cust_a, Customer)
    assert isinstance(tech1, Technician)
    assert isinstance(svc_screen, Service)

    off_date = date.today() + timedelta(days=60)
    res = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "technician_id": str(tech1.id),
            "service_id": str(svc_screen.id),
            "appointment_date": off_date.isoformat(),
            "start_time": "09:00",
        },
    )
    assert res.status_code == 400


def test_create_booking_database_error_rollback(
    client: TestClient,
    booking_test_env: dict[str, object],
    db: Session,
) -> None:
    """8. Lỗi database trong quá trình tạo đặt chỗ kích hoạt rollback sạch sẽ."""
    cust_a = booking_test_env["customer_a"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    count_before = len(db.exec(select(Appointment)).all())

    with patch.object(
        Session, "commit", side_effect=RuntimeError("Lỗi kết nối database giả lập")
    ):
        res = client.post(
            "/api/bookings",
            json={
                "customer_id": str(cust_a.id),
                "service_id": str(svc_screen.id),
                "appointment_date": t_date.isoformat(),
                "start_time": "15:00",
            },
        )
        assert res.status_code == 500
        assert "Lỗi hệ thống" in res.json()["detail"]

    count_after = len(db.exec(select(Appointment)).all())
    assert count_after == count_before


# ============================================================================
# API 2: UPDATE BOOKING TESTS (PATCH /api/bookings/{id})
# ============================================================================


def test_update_booking_success(
    client: TestClient,
    booking_test_env: dict[str, object],
    db: Session,
) -> None:
    """9. Cập nhật đổi ngày giờ và kỹ thuật viên thành công (HTTP 200)."""
    cust_a = booking_test_env["customer_a"]
    tech1 = booking_test_env["tech1"]
    tech2 = booking_test_env["tech2"]
    svc_battery = booking_test_env["svc_battery"]
    t_date = booking_test_env["target_date"]
    user_a = booking_test_env["user_a"]
    assert isinstance(cust_a, Customer)
    assert isinstance(tech1, Technician)
    assert isinstance(tech2, Technician)
    assert isinstance(svc_battery, Service)
    assert isinstance(t_date, date)
    assert isinstance(user_a, User)

    # 1. Tạo đặt chỗ ban đầu vào 13:00 với tech1
    create_res = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_battery.id),
            "technician_id": str(tech1.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "13:00",
        },
    )
    booking_id = create_res.json()["appointment_id"]

    cust_a_headers = authentication_token_from_email(
        client=client, email=user_a.email, db=db
    )

    # 2. Đổi sang 15:00 với tech2 kèm lý do đổi lịch
    patch_res = client.patch(
        f"/api/bookings/{booking_id}",
        headers=cust_a_headers,
        json={
            "start_time": "15:00",
            "technician_id": str(tech2.id),
            "reschedule_reason": "Đổi sang giờ chiều rảnh hơn",
            "description": "Ghi chú mới sau khi đổi",
        },
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["start_time"] == "15:00"

    # Verify DB
    appt = db.get(Appointment, uuid.UUID(booking_id))
    assert appt is not None
    assert appt.appointment_date.time() == time(15, 0)
    assert appt.technician_id == tech2.id
    assert appt.customer_notes == "Ghi chú mới sau khi đổi"

    # Verify audit history notes reschedule reason
    histories = db.exec(
        select(RepairStatusHistory).where(RepairStatusHistory.appointment_id == appt.id)
    ).all()
    assert any("Đổi sang giờ chiều" in (h.note or "") for h in histories)


def test_update_booking_not_found_404(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """10. Cập nhật đặt chỗ không tồn tại trả về 404 Not Found."""
    fake_id = uuid.uuid4()
    res = client.patch(
        f"/api/bookings/{fake_id}",
        headers=superuser_token_headers,
        json={"start_time": "10:00"},
    )
    assert res.status_code == 404


def test_update_booking_unauthorized_403(
    client: TestClient,
    booking_test_env: dict[str, object],
    db: Session,
) -> None:
    """11. Khách hàng B cố tình sửa đặt chỗ của Khách hàng A bị từ chối 403 Forbidden."""
    cust_a = booking_test_env["customer_a"]
    svc_battery = booking_test_env["svc_battery"]
    t_date = booking_test_env["target_date"]
    user_b = booking_test_env["user_b"]
    assert isinstance(cust_a, Customer)
    assert isinstance(svc_battery, Service)
    assert isinstance(t_date, date)
    assert isinstance(user_b, User)

    create_res = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_battery.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "16:00",
        },
    )
    booking_id = create_res.json()["appointment_id"]

    cust_b_headers = authentication_token_from_email(
        client=client, email=user_b.email, db=db
    )

    res = client.patch(
        f"/api/bookings/{booking_id}",
        headers=cust_b_headers,
        json={"start_time": "16:30"},
    )
    assert res.status_code == 403
    assert "Không đủ quyền" in res.json()["detail"]


def test_update_booking_slot_conflict_409(
    client: TestClient,
    booking_test_env: dict[str, object],
) -> None:
    """12. Đổi lịch sang khung giờ đã bị trùng với lịch hẹn khác trả về 409 Conflict."""
    cust_a = booking_test_env["customer_a"]
    tech1 = booking_test_env["tech1"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(tech1, Technician)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    # Appt 1: 08:00 - 09:00
    client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "technician_id": str(tech1.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "08:00",
        },
    )

    # Appt 2: 11:00 - 12:00
    res2 = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "technician_id": str(tech1.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "11:00",
        },
    )
    appt2_id = res2.json()["appointment_id"]

    # Đổi Appt 2 sang 08:30 (trùng với Appt 1 08:00-09:00)
    patch_res = client.patch(
        f"/api/bookings/{appt2_id}",
        json={"start_time": "08:30"},
    )
    assert patch_res.status_code == 409
    assert "trùng" in patch_res.json()["detail"].lower()


def test_update_booking_disallowed_status_409(
    client: TestClient,
    booking_test_env: dict[str, object],
    db: Session,
) -> None:
    """13. Không thể sửa đặt chỗ đã bị hủy hoặc đã hoàn thành (409 Conflict)."""
    cust_a = booking_test_env["customer_a"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    res = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "12:00",
        },
    )
    booking_id = res.json()["appointment_id"]

    # Set status CANCELLED
    appt = db.get(Appointment, uuid.UUID(booking_id))
    assert appt is not None
    appt.status = "CANCELLED"
    db.add(appt)
    db.commit()

    patch_res = client.patch(
        f"/api/bookings/{booking_id}",
        json={"start_time": "12:30"},
    )
    assert patch_res.status_code == 409
    assert "đã bị hủy" in patch_res.json()["detail"].lower()


# ============================================================================
# API 3: CANCEL BOOKING TESTS (PATCH /api/bookings/{id}/cancel)
# ============================================================================


def test_cancel_booking_success(
    client: TestClient,
    booking_test_env: dict[str, object],
    db: Session,
) -> None:
    """14. Khách hàng sở hữu hủy đặt chỗ thành công kèm lý do hủy (HTTP 200)."""
    cust_a = booking_test_env["customer_a"]
    user_a = booking_test_env["user_a"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(user_a, User)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    create_res = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
        },
    )
    booking_id = create_res.json()["appointment_id"]

    cust_a_headers = authentication_token_from_email(
        client=client, email=user_a.email, db=db
    )

    cancel_res = client.patch(
        f"/api/bookings/{booking_id}/cancel",
        headers=cust_a_headers,
        json={"reason": "Tôi tìm được chỗ sửa gần nhà hơn", "note": "Xin lỗi cửa hàng"},
    )
    assert cancel_res.status_code == 200
    data = cancel_res.json()
    assert data["success"] is True
    assert data["data"]["status"] == "CANCELLED"
    assert data["data"]["cancellation_reason"] == "Tôi tìm được chỗ sửa gần nhà hơn"

    # Verify DB: Không xóa vật lý
    appt = db.get(Appointment, uuid.UUID(booking_id))
    assert appt is not None
    assert appt.status == "CANCELLED"
    assert appt.cancellation_reason == "Tôi tìm được chỗ sửa gần nhà hơn"


def test_cancel_booking_not_found_404(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """15. Hủy đặt chỗ với ID không tồn tại trả về 404 Not Found."""
    fake_id = uuid.uuid4()
    res = client.patch(
        f"/api/bookings/{fake_id}/cancel",
        headers=superuser_token_headers,
        json={"reason": "Lý do hợp lệ"},
    )
    assert res.status_code == 404


def test_cancel_booking_unauthorized_403(
    client: TestClient,
    booking_test_env: dict[str, object],
    db: Session,
) -> None:
    """16. Khách hàng B cố tình hủy đặt chỗ của khách hàng A bị chặn 403 Forbidden."""
    cust_a = booking_test_env["customer_a"]
    user_b = booking_test_env["user_b"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(user_b, User)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    create_res = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "10:00",
        },
    )
    booking_id = create_res.json()["appointment_id"]

    cust_b_headers = authentication_token_from_email(
        client=client, email=user_b.email, db=db
    )

    res = client.patch(
        f"/api/bookings/{booking_id}/cancel",
        headers=cust_b_headers,
        json={"reason": "Cố tình hủy lén"},
    )
    assert res.status_code == 403
    assert "Không đủ quyền" in res.json()["detail"]


def test_cancel_booking_missing_reason_422(
    client: TestClient,
    booking_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
) -> None:
    """17. Thiếu lý do hủy hoặc để khoảng trắng trả về 422 Unprocessable Entity."""
    cust_a = booking_test_env["customer_a"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    create_res = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "11:00",
        },
    )
    booking_id = create_res.json()["appointment_id"]

    # 17a. Không có reason
    res_empty = client.patch(
        f"/api/bookings/{booking_id}/cancel",
        headers=superuser_token_headers,
        json={},
    )
    assert res_empty.status_code == 422

    # 17b. Reason chỉ có khoảng trắng
    res_blank = client.patch(
        f"/api/bookings/{booking_id}/cancel",
        headers=superuser_token_headers,
        json={"reason": "   "},
    )
    assert res_blank.status_code == 422


def test_cancel_booking_disallowed_status_409(
    client: TestClient,
    booking_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """18. Không thể hủy lịch hẹn đã hoàn tất hoặc đang sửa chữa (409 Conflict)."""
    cust_a = booking_test_env["customer_a"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    create_res = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "13:00",
        },
    )
    booking_id = create_res.json()["appointment_id"]

    # Cập nhật trạng thái COMPLETED
    appt = db.get(Appointment, uuid.UUID(booking_id))
    assert appt is not None
    appt.status = "COMPLETED"
    db.add(appt)
    db.commit()

    res = client.patch(
        f"/api/bookings/{booking_id}/cancel",
        headers=superuser_token_headers,
        json={"reason": "Cố hủy lịch đã xong"},
    )
    assert res.status_code == 409
    assert "đã hoàn tất" in res.json()["detail"]


def test_cancel_booking_repeated_consistent_handling(
    client: TestClient,
    booking_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """19. Hủy đặt chỗ lặp lại được xử lý nhất quán (409 Conflict) và không tạo tác dụng phụ."""
    cust_a = booking_test_env["customer_a"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    create_res = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "14:00",
        },
    )
    booking_id = create_res.json()["appointment_id"]

    # Lần hủy 1: Thành công
    res1 = client.patch(
        f"/api/bookings/{booking_id}/cancel",
        headers=superuser_token_headers,
        json={"reason": "Hủy lần đầu"},
    )
    assert res1.status_code == 200

    histories_count1 = len(
        db.exec(
            select(RepairStatusHistory).where(
                RepairStatusHistory.appointment_id == uuid.UUID(booking_id)
            )
        ).all()
    )

    # Lần hủy 2: Báo lỗi 409 nhất quán
    res2 = client.patch(
        f"/api/bookings/{booking_id}/cancel",
        headers=superuser_token_headers,
        json={"reason": "Hủy lần thứ hai"},
    )
    assert res2.status_code == 409
    assert "đã bị hủy" in res2.json()["detail"]

    # Không tạo thêm bản ghi history trùng lặp
    histories_count2 = len(
        db.exec(
            select(RepairStatusHistory).where(
                RepairStatusHistory.appointment_id == uuid.UUID(booking_id)
            )
        ).all()
    )
    assert histories_count2 == histories_count1


def test_cancel_booking_database_error_rollback(
    client: TestClient,
    booking_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """20. Lỗi database trong quá trình hủy kích hoạt rollback an toàn và trả về 500."""
    cust_a = booking_test_env["customer_a"]
    svc_screen = booking_test_env["svc_screen"]
    t_date = booking_test_env["target_date"]
    assert isinstance(cust_a, Customer)
    assert isinstance(svc_screen, Service)
    assert isinstance(t_date, date)

    create_res = client.post(
        "/api/bookings",
        json={
            "customer_id": str(cust_a.id),
            "service_id": str(svc_screen.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "16:00",
        },
    )
    booking_id = create_res.json()["appointment_id"]

    with patch.object(
        Session, "commit", side_effect=RuntimeError("Lỗi kết nối cơ sở dữ liệu")
    ):
        res = client.patch(
            f"/api/bookings/{booking_id}/cancel",
            headers=superuser_token_headers,
            json={"reason": "Khách hủy lịch"},
        )
        assert res.status_code == 500
        assert "Lỗi hệ thống" in res.json()["detail"]

    # Đảm bảo trạng thái vẫn là PENDING do đã rollback
    db.expire_all()
    appt = db.get(Appointment, uuid.UUID(booking_id))
    assert appt is not None
    assert appt.status == "PENDING"
