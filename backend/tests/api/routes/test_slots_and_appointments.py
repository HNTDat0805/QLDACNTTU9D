import uuid
from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import (
    Appointment,
    Customer,
    Device,
    Service,
    Technician,
    TechnicianSchedule,
    User,
)


@pytest.fixture
def setup_test_data(db: Session) -> dict[str, object]:
    """Setup clean isolated test customer, device, technician, schedule and services."""
    # User for customer
    user = User(
        email=f"test_cust_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashedpassword123",
        role="customer",
    )
    db.add(user)
    db.flush()

    # Customer
    customer = Customer(
        full_name="Nguyễn Văn Test",
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
        user_id=user.id,
    )
    db.add(customer)
    db.flush()

    # Device
    device = Device(
        customer_id=customer.id,
        device_type="Smartphone",
        brand="Apple",
        model="iPhone 14 Pro",
    )
    db.add(device)
    db.flush()

    # Technician
    tech = Technician(
        full_name="Lê Văn Kỹ Thuật",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
        specialization="Phần cứng",
        is_active=True,
    )
    db.add(tech)
    db.flush()

    # Service 1: 60 mins
    svc_60 = Service(
        name=f"Thay màn hình {uuid.uuid4().hex[:6]}",
        base_price=1_500_000.0,
        estimated_duration_minutes=60,
        is_active=True,
    )
    # Service 2: 30 mins
    svc_30 = Service(
        name=f"Vệ sinh máy {uuid.uuid4().hex[:6]}",
        base_price=150_000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    db.add(svc_60)
    db.add(svc_30)
    db.flush()

    # Working schedule for next week
    test_date = date.today() + timedelta(days=14)
    schedule = TechnicianSchedule(
        technician_id=tech.id,
        work_date=test_date,
        start_time=time(8, 0),
        end_time=time(17, 0),
        status="AVAILABLE",
    )
    db.add(schedule)
    db.commit()

    return {
        "customer": customer,
        "device": device,
        "technician": tech,
        "service_60": svc_60,
        "service_30": svc_30,
        "test_date": test_date,
    }


# ============================================================================
# 1. REQUEST HỢP LỆ VÀ KIỂM TRA ĐẦU RA API 1
# ============================================================================


def test_get_available_slots_valid(
    client: TestClient, setup_test_data: dict[str, object]
) -> None:
    svc = setup_test_data["service_60"]
    tech = setup_test_data["technician"]
    t_date = setup_test_data["test_date"]
    assert isinstance(svc, Service)
    assert isinstance(tech, Technician)
    assert isinstance(t_date, date)

    # API 1 via /api/v1/slots/available
    response = client.get(
        "/api/v1/slots/available",
        params={
            "date": t_date.isoformat(),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == t_date.isoformat()
    assert data["service_id"] == str(svc.id)
    assert len(data["available_slots"]) > 0
    # First slot should be 08:00 -> 09:00
    first_slot = data["available_slots"][0]
    assert first_slot["start_time"] == "08:00"
    assert first_slot["end_time"] == "09:00"
    assert first_slot["available"] is True

    # Test alias route /api/slots/available
    resp_alias = client.get(
        "/api/slots/available",
        params={
            "date": t_date.isoformat(),
            "service_id": str(svc.id),
        },
    )
    assert resp_alias.status_code == 200


# ============================================================================
# 2. NGÀY HOẶC GIỜ SAI ĐỊNH DẠNG
# ============================================================================


def test_invalid_date_or_time_format(
    client: TestClient, setup_test_data: dict[str, object]
) -> None:
    svc = setup_test_data["service_60"]
    assert isinstance(svc, Service)

    # Invalid date string in GET
    resp = client.get(
        "/api/v1/slots/available",
        params={"date": "invalid-date-2026", "service_id": str(svc.id)},
    )
    assert resp.status_code == 422

    # Invalid time string in POST /check
    resp_check = client.post(
        "/api/v1/slots/check",
        json={
            "service_id": str(svc.id),
            "appointment_date": "2026-10-15",
            "start_time": "99:99",
        },
    )
    assert resp_check.status_code == 422


# ============================================================================
# 3. DỊCH VỤ HOẶC KỸ THUẬT VIÊN KHÔNG TỒN TẠI
# ============================================================================


def test_service_or_technician_not_found(
    client: TestClient, setup_test_data: dict[str, object]
) -> None:
    t_date = setup_test_data["test_date"]
    assert isinstance(t_date, date)
    non_existent_id = str(uuid.uuid4())

    # Service 404 in GET /available
    resp1 = client.get(
        "/api/v1/slots/available",
        params={"date": t_date.isoformat(), "service_id": non_existent_id},
    )
    assert resp1.status_code == 404

    # Tech 404 in POST /check
    svc = setup_test_data["service_60"]
    assert isinstance(svc, Service)
    resp2 = client.post(
        "/api/v1/slots/check",
        json={
            "service_id": str(svc.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
            "technician_id": non_existent_id,
        },
    )
    assert resp2.status_code == 404


# ============================================================================
# 4. SLOT CÒN TRỐNG (API 4)
# ============================================================================


def test_slot_is_available(
    client: TestClient, setup_test_data: dict[str, object]
) -> None:
    svc = setup_test_data["service_60"]
    tech = setup_test_data["technician"]
    t_date = setup_test_data["test_date"]
    assert isinstance(svc, Service)
    assert isinstance(tech, Technician)
    assert isinstance(t_date, date)

    resp = client.post(
        "/api/v1/slots/check",
        json={
            "service_id": str(svc.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
            "technician_id": str(tech.id),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True
    assert data["reason"] is None
    assert data["start_time"] == "09:00"
    assert data["end_time"] == "10:00"


# ============================================================================
# 5. SLOT ĐÃ BỊ ĐẶT (API 2 -> API 4)
# ============================================================================


def test_slot_already_booked(
    client: TestClient, setup_test_data: dict[str, object]
) -> None:
    cust = setup_test_data["customer"]
    dev = setup_test_data["device"]
    svc = setup_test_data["service_60"]
    tech = setup_test_data["technician"]
    t_date = setup_test_data["test_date"]
    assert isinstance(cust, Customer)
    assert isinstance(dev, Device)
    assert isinstance(svc, Service)
    assert isinstance(tech, Technician)
    assert isinstance(t_date, date)

    # Book slot at 09:00 (duration 60m -> 09:00-10:00)
    create_resp = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "device_id": str(dev.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
            "description": "Màn hình bị sọc",
        },
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["status"] == "PENDING"
    assert "appointment_code" in created_data

    # Now verify slot 09:00 is UNAVAILABLE
    check_resp = client.post(
        "/api/v1/slots/check",
        json={
            "service_id": str(svc.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
            "technician_id": str(tech.id),
        },
    )
    assert check_resp.status_code == 200
    check_data = check_resp.json()
    assert check_data["available"] is False
    assert check_data["reason"] == "SLOT_UNAVAILABLE"


# ============================================================================
# 6. HAI LỊCH CHỒNG LẤN MỘT PHẦN
# ============================================================================


def test_partial_overlap_conflict(
    client: TestClient, setup_test_data: dict[str, object]
) -> None:
    cust = setup_test_data["customer"]
    dev = setup_test_data["device"]
    svc = setup_test_data["service_60"]
    tech = setup_test_data["technician"]
    t_date = setup_test_data["test_date"]
    assert isinstance(cust, Customer)
    assert isinstance(dev, Device)
    assert isinstance(svc, Service)
    assert isinstance(tech, Technician)
    assert isinstance(t_date, date)

    # Book 10:00 - 11:00
    client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "device_id": str(dev.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "10:00",
        },
    )

    # Overlap test 1: candidate starts at 09:30 (ends 10:30 -> overlaps 10:00-10:30)
    resp_overlap1 = client.post(
        "/api/v1/slots/check",
        json={
            "service_id": str(svc.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:30",
            "technician_id": str(tech.id),
        },
    )
    assert resp_overlap1.json()["available"] is False

    # Overlap test 2: candidate starts at 10:30 (ends 11:30 -> overlaps 10:30-11:00)
    resp_overlap2 = client.post(
        "/api/v1/slots/check",
        json={
            "service_id": str(svc.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "10:30",
            "technician_id": str(tech.id),
        },
    )
    assert resp_overlap2.json()["available"] is False

    # Non-overlap test: starts at 11:00 (ends 12:00 -> touches endpoint, no overlap)
    resp_free = client.post(
        "/api/v1/slots/check",
        json={
            "service_id": str(svc.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "11:00",
            "technician_id": str(tech.id),
        },
    )
    assert resp_free.json()["available"] is True


# ============================================================================
# 7. NGÀY NẰM NGOÀI LỊCH LÀM VIỆC
# ============================================================================


def test_date_outside_working_schedule(
    client: TestClient, setup_test_data: dict[str, object]
) -> None:
    cust = setup_test_data["customer"]
    svc = setup_test_data["service_60"]
    tech = setup_test_data["technician"]
    assert isinstance(cust, Customer)
    assert isinstance(svc, Service)
    assert isinstance(tech, Technician)

    # Day without schedule (e.g. 50 days in the future)
    no_work_date = date.today() + timedelta(days=50)

    # GET /available returns empty list
    resp_avail = client.get(
        "/api/v1/slots/available",
        params={
            "date": no_work_date.isoformat(),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
        },
    )
    assert resp_avail.status_code == 200
    assert resp_avail.json()["available_slots"] == []

    # POST /appointments fails with 400
    resp_book = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": no_work_date.isoformat(),
            "start_time": "09:00",
        },
    )
    assert resp_book.status_code == 400


# ============================================================================
# 8. TẠO LỊCH THẤT BẠI KHÔNG ĐỂ LẠI DỮ LIỆU KHÔNG NHẤT QUÁN
# ============================================================================


def test_create_appointment_failure_rollback(
    client: TestClient, setup_test_data: dict[str, object], db: Session
) -> None:
    cust = setup_test_data["customer"]
    dev = setup_test_data["device"]
    svc = setup_test_data["service_60"]
    tech = setup_test_data["technician"]
    t_date = setup_test_data["test_date"]
    assert isinstance(cust, Customer)
    assert isinstance(dev, Device)
    assert isinstance(svc, Service)
    assert isinstance(tech, Technician)
    assert isinstance(t_date, date)

    # 1. Book first appointment at 08:00
    client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "device_id": str(dev.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "08:00",
        },
    )

    count_before = len(db.exec(select(Appointment)).all())

    # 2. Attempt duplicate booking at 08:00
    fail_resp = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "device_id": str(dev.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "08:00",
        },
    )
    assert fail_resp.status_code == 409

    # Verify no partial appointment inserted
    count_after = len(db.exec(select(Appointment)).all())
    assert count_after == count_before


# ============================================================================
# 9. CẬP NHẬT LỊCH SANG SLOT KHÔNG HỢP LỆ PHẢI GIỮ NGUYÊN DỮ LIỆU CŨ
# ============================================================================


def test_update_appointment_invalid_slot_retains_old_data(
    client: TestClient, setup_test_data: dict[str, object], db: Session
) -> None:
    cust = setup_test_data["customer"]
    dev = setup_test_data["device"]
    svc = setup_test_data["service_60"]
    tech = setup_test_data["technician"]
    t_date = setup_test_data["test_date"]
    assert isinstance(cust, Customer)
    assert isinstance(dev, Device)
    assert isinstance(svc, Service)
    assert isinstance(tech, Technician)
    assert isinstance(t_date, date)

    # Appt 1: 08:00 - 09:00
    client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "device_id": str(dev.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "08:00",
        },
    )

    # Appt 2: 14:00 - 15:00
    res2 = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "device_id": str(dev.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "14:00",
        },
    )
    appt2_id = res2.json()["appointment_id"]

    # Attempt to move Appt 2 to 08:30 (conflicts with Appt 1)
    patch_resp = client.patch(
        f"/api/v1/appointments/{appt2_id}",
        json={"start_time": "08:30"},
    )
    assert patch_resp.status_code == 409

    # Verify Appt 2 still retains 14:00 in DB
    refreshed_appt2 = db.get(Appointment, uuid.UUID(appt2_id))
    assert refreshed_appt2 is not None
    assert refreshed_appt2.appointment_date.time() == time(14, 0)


# ============================================================================
# 10. CẬP NHẬT LỊCH KHÔNG ĐỔI GIỜ KHÔNG TỰ XUNG ĐỘT VỚI CHÍNH NÓ
# ============================================================================


def test_update_appointment_same_slot_no_self_conflict(
    client: TestClient, setup_test_data: dict[str, object]
) -> None:
    cust = setup_test_data["customer"]
    dev = setup_test_data["device"]
    svc = setup_test_data["service_60"]
    tech = setup_test_data["technician"]
    t_date = setup_test_data["test_date"]
    assert isinstance(cust, Customer)
    assert isinstance(dev, Device)
    assert isinstance(svc, Service)
    assert isinstance(tech, Technician)
    assert isinstance(t_date, date)

    # Book at 13:00
    res = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "device_id": str(dev.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "13:00",
            "description": "Ghi chú ban đầu",
        },
    )
    appt_id = res.json()["appointment_id"]

    # Update description without changing time (should succeed, not self-conflict)
    patch_res = client.patch(
        f"/api/v1/appointments/{appt_id}",
        json={
            "start_time": "13:00",
            "description": "Ghi chú đã cập nhật",
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["message"] == "Cập nhật lịch hẹn thành công"


# ============================================================================
# 11. HAI REQUEST ĐỒNG THỜI CỐ ĐẶT CÙNG TÀI NGUYÊN VÀ THỜI GIAN
# ============================================================================


def test_concurrent_booking_conflict_prevention(
    client: TestClient, setup_test_data: dict[str, object]
) -> None:
    cust = setup_test_data["customer"]
    dev = setup_test_data["device"]
    svc = setup_test_data["service_60"]
    tech = setup_test_data["technician"]
    t_date = setup_test_data["test_date"]
    assert isinstance(cust, Customer)
    assert isinstance(dev, Device)
    assert isinstance(svc, Service)
    assert isinstance(tech, Technician)
    assert isinstance(t_date, date)

    # Request 1 wins
    res1 = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "device_id": str(dev.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "15:00",
        },
    )
    assert res1.status_code == 201

    # Request 2 attempting same slot must be rejected with 409
    res2 = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "device_id": str(dev.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "15:00",
        },
    )
    assert res2.status_code == 409
    assert (
        "trùng" in res2.json()["detail"].lower()
        or "đã có" in res2.json()["detail"].lower()
    )


# ============================================================================
# 12. LỊCH ĐÃ HỦY ĐƯỢC XỬ LÝ ĐÚNG THEO QUY TẮC GIẢI PHÓNG SLOT
# ============================================================================


def test_cancelled_appointment_frees_slot(
    client: TestClient, setup_test_data: dict[str, object], db: Session
) -> None:
    cust = setup_test_data["customer"]
    dev = setup_test_data["device"]
    svc = setup_test_data["service_60"]
    tech = setup_test_data["technician"]
    t_date = setup_test_data["test_date"]
    assert isinstance(cust, Customer)
    assert isinstance(dev, Device)
    assert isinstance(svc, Service)
    assert isinstance(tech, Technician)
    assert isinstance(t_date, date)

    # 1. Book at 16:00
    res = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "device_id": str(dev.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "16:00",
        },
    )
    appt_id = res.json()["appointment_id"]

    # 2. Cancel appointment
    appt = db.get(Appointment, uuid.UUID(appt_id))
    assert appt is not None
    appt.status = "CANCELLED"
    db.add(appt)
    db.commit()

    # 3. Verify slot 16:00 is available again in POST /check
    check_res = client.post(
        "/api/v1/slots/check",
        json={
            "service_id": str(svc.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "16:00",
            "technician_id": str(tech.id),
        },
    )
    assert check_res.json()["available"] is True

    # 4. A new appointment can now be booked at 16:00
    rebook_res = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust.id),
            "device_id": str(dev.id),
            "service_id": str(svc.id),
            "technician_id": str(tech.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "16:00",
        },
    )
    assert rebook_res.status_code == 201
