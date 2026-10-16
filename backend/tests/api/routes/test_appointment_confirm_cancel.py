import uuid
from datetime import UTC, date, datetime, time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import (
    Appointment,
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
def appointment_test_env(db: Session) -> dict[str, object]:
    """Create test environment with customers, technician, and appointments."""
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
        phone_number=f"097{uuid.uuid4().int % 10000000:07d}",
        user_id=user_a.id,
    )
    cust_b = Customer(
        full_name="Trần Thị B",
        phone_number=f"096{uuid.uuid4().int % 10000000:07d}",
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
        model="iPhone 13",
    )
    db.add(dev_a)
    db.flush()

    # Technician
    tech = Technician(
        full_name="Nguyễn Kỹ Thuật",
        phone_number=f"093{uuid.uuid4().int % 10000000:07d}",
        specialization="Màn hình",
        is_active=True,
    )
    db.add(tech)
    db.flush()

    # Schedule
    test_d = date(2026, 10, 28)
    sched = TechnicianSchedule(
        technician_id=tech.id,
        work_date=test_d,
        start_time=time(8, 0),
        end_time=time(17, 0),
        status="AVAILABLE",
    )
    db.add(sched)

    # Service
    svc = Service(
        name=f"Thay pin test {uuid.uuid4().hex[:4]}",
        base_price=300000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    db.add(svc)
    db.flush()

    # Appointment PENDING for customer A
    appt = Appointment(
        appointment_number=f"APPT-TEST-{uuid.uuid4().hex[:6].upper()}",
        appointment_date=datetime.combine(test_d, time(9, 0), tzinfo=UTC),
        status="PENDING",
        customer_id=cust_a.id,
        device_id=dev_a.id,
        technician_id=tech.id,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    return {
        "user_a": user_a,
        "user_b": user_b,
        "user_staff": user_staff,
        "customer_a": cust_a,
        "customer_b": cust_b,
        "technician": tech,
        "service": svc,
        "appointment": appt,
        "test_date": test_d,
    }


# ============================================================================
# TESTS: API 1 - CONFIRM APPOINTMENT
# ============================================================================


def test_confirm_appointment_success(
    client: TestClient,
    appointment_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Test 1: Admin/Staff confirms valid pending appointment successfully."""
    appt = appointment_test_env["appointment"]
    assert isinstance(appt, Appointment)

    response = client.patch(
        f"/api/v1/appointments/{appt.id}/confirm",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["message"] == "Xác nhận lịch hẹn thành công"
    assert res_data["data"]["id"] == str(appt.id)
    assert res_data["data"]["status"] == "CONFIRMED"

    # Verify DB update
    db.refresh(appt)
    assert appt.status == "CONFIRMED"

    # Verify audit history
    histories = db.exec(
        select(RepairStatusHistory).where(RepairStatusHistory.appointment_id == appt.id)
    ).all()
    assert any(h.new_status == "CONFIRMED" for h in histories)


def test_confirm_appointment_with_staff_role(
    client: TestClient,
    appointment_test_env: dict[str, object],
    db: Session,
) -> None:
    """Test 2: Staff role user can confirm appointment."""
    appt = appointment_test_env["appointment"]
    user_staff = appointment_test_env["user_staff"]
    assert isinstance(appt, Appointment)
    assert isinstance(user_staff, User)

    staff_headers = authentication_token_from_email(
        client=client, email=user_staff.email, db=db
    )
    # Reset status to PENDING
    appt.status = "PENDING"
    db.add(appt)
    db.commit()

    # Call with direct /api prefix
    response = client.patch(
        f"/api/appointments/{appt.id}/confirm",
        headers=staff_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "CONFIRMED"


def test_confirm_appointment_not_found(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """Test 3: Confirm with non-existent appointment ID returns 404."""
    fake_id = uuid.uuid4()
    response = client.patch(
        f"/api/v1/appointments/{fake_id}/confirm",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


def test_confirm_appointment_already_cancelled_or_completed_conflict(
    client: TestClient,
    appointment_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Test 4: Cannot confirm appointment that is CANCELLED or COMPLETED (409 Conflict)."""
    appt = appointment_test_env["appointment"]
    assert isinstance(appt, Appointment)

    # 4a. CANCELLED -> 409
    appt.status = "CANCELLED"
    db.add(appt)
    db.commit()

    res_cancel = client.patch(
        f"/api/v1/appointments/{appt.id}/confirm",
        headers=superuser_token_headers,
    )
    assert res_cancel.status_code == 409
    assert "đã bị hủy" in res_cancel.json()["detail"]

    # 4b. COMPLETED -> 409
    appt.status = "COMPLETED"
    db.add(appt)
    db.commit()

    res_comp = client.patch(
        f"/api/v1/appointments/{appt.id}/confirm",
        headers=superuser_token_headers,
    )
    assert res_comp.status_code == 409
    assert "đã hoàn tất" in res_comp.json()["detail"]


def test_confirm_appointment_customer_lacks_permission(
    client: TestClient,
    appointment_test_env: dict[str, object],
    db: Session,
) -> None:
    """Test 5: Customer user cannot confirm appointments (403 Forbidden)."""
    appt = appointment_test_env["appointment"]
    user_a = appointment_test_env["user_a"]
    assert isinstance(appt, Appointment)
    assert isinstance(user_a, User)

    cust_headers = authentication_token_from_email(
        client=client, email=user_a.email, db=db
    )

    response = client.patch(
        f"/api/v1/appointments/{appt.id}/confirm",
        headers=cust_headers,
    )
    assert response.status_code == 403
    assert "Không đủ quyền" in response.json()["detail"]


def test_confirm_appointment_unauthenticated(
    client: TestClient,
    appointment_test_env: dict[str, object],
) -> None:
    """Test 6: Request without token returns 401 Unauthorized."""
    appt = appointment_test_env["appointment"]
    assert isinstance(appt, Appointment)

    response = client.patch(f"/api/v1/appointments/{appt.id}/confirm")
    assert response.status_code == 401


def test_confirm_appointment_idempotent(
    client: TestClient,
    appointment_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Test 7: Idempotency: Calling confirm multiple times returns 200 without duplicate side effects."""
    appt = appointment_test_env["appointment"]
    assert isinstance(appt, Appointment)

    # First call: updates to CONFIRMED
    res1 = client.patch(
        f"/api/v1/appointments/{appt.id}/confirm",
        headers=superuser_token_headers,
    )
    assert res1.status_code == 200
    assert res1.json()["data"]["status"] == "CONFIRMED"

    # Count history entries
    h_count1 = len(
        db.exec(
            select(RepairStatusHistory).where(
                RepairStatusHistory.appointment_id == appt.id
            )
        ).all()
    )

    # Second call: idempotent, doesn't add new history
    res2 = client.patch(
        f"/api/v1/appointments/{appt.id}/confirm",
        headers=superuser_token_headers,
    )
    assert res2.status_code == 200
    assert res2.json()["success"] is True
    assert "trước đó" in res2.json()["message"]

    h_count2 = len(
        db.exec(
            select(RepairStatusHistory).where(
                RepairStatusHistory.appointment_id == appt.id
            )
        ).all()
    )
    assert h_count1 == h_count2


# ============================================================================
# TESTS: API 2 - CANCEL APPOINTMENT
# ============================================================================


def test_cancel_appointment_success(
    client: TestClient,
    appointment_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Test 8: Admin/Staff cancels valid appointment with reason and note."""
    appt = appointment_test_env["appointment"]
    assert isinstance(appt, Appointment)

    # Reset to PENDING
    appt.status = "PENDING"
    db.add(appt)
    db.commit()

    cancel_payload = {
        "reason": "Khách bận việc gia đình đột xuất",
        "note": "Khách xin dời sang tuần sau",
    }
    response = client.patch(
        f"/api/v1/appointments/{appt.id}/cancel",
        headers=superuser_token_headers,
        json=cancel_payload,
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["message"] == "Hủy lịch hẹn thành công"
    assert res_data["data"]["id"] == str(appt.id)
    assert res_data["data"]["status"] == "CANCELLED"
    assert res_data["data"]["cancellation_reason"] == cancel_payload["reason"]

    # Verify DB record
    db.refresh(appt)
    assert appt.status == "CANCELLED"
    assert appt.cancellation_reason == cancel_payload["reason"]
    assert "tuần sau" in (appt.customer_notes or "")

    # Verify audit history
    history = db.exec(
        select(RepairStatusHistory)
        .where(RepairStatusHistory.appointment_id == appt.id)
        .where(RepairStatusHistory.new_status == "CANCELLED")
    ).first()
    assert history is not None
    assert cancel_payload["reason"] in (history.note or "")


def test_cancel_appointment_by_owner_customer(
    client: TestClient,
    appointment_test_env: dict[str, object],
    db: Session,
) -> None:
    """Test 9: The customer who owns the appointment can cancel their own booking."""
    appt = appointment_test_env["appointment"]
    user_a = appointment_test_env["user_a"]
    assert isinstance(appt, Appointment)
    assert isinstance(user_a, User)

    # Reset status
    appt.status = "PENDING"
    db.add(appt)
    db.commit()

    cust_a_headers = authentication_token_from_email(
        client=client, email=user_a.email, db=db
    )

    response = client.patch(
        f"/api/appointments/{appt.id}/cancel",
        headers=cust_a_headers,
        json={"reason": "Tôi có lịch bận đột xuất"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "CANCELLED"


def test_cancel_appointment_not_found(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """Test 10: Cancel non-existent appointment ID returns 404."""
    fake_id = uuid.uuid4()
    response = client.patch(
        f"/api/v1/appointments/{fake_id}/cancel",
        headers=superuser_token_headers,
        json={"reason": "Lý do hợp lệ"},
    )
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


def test_cancel_appointment_already_cancelled_or_completed_conflict(
    client: TestClient,
    appointment_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Test 11: Cannot cancel appointment that is already CANCELLED or COMPLETED (409 Conflict)."""
    appt = appointment_test_env["appointment"]
    assert isinstance(appt, Appointment)

    # 11a. CANCELLED -> 409
    appt.status = "CANCELLED"
    db.add(appt)
    db.commit()

    res_canc = client.patch(
        f"/api/v1/appointments/{appt.id}/cancel",
        headers=superuser_token_headers,
        json={"reason": "Hủy thêm lần nữa"},
    )
    assert res_canc.status_code == 409
    assert "đã bị hủy" in res_canc.json()["detail"]

    # 11b. COMPLETED -> 409
    appt.status = "COMPLETED"
    db.add(appt)
    db.commit()

    res_comp = client.patch(
        f"/api/v1/appointments/{appt.id}/cancel",
        headers=superuser_token_headers,
        json={"reason": "Cố hủy lịch đã xong"},
    )
    assert res_comp.status_code == 409
    assert "đã hoàn tất" in res_comp.json()["detail"]


def test_cancel_appointment_invalid_input_payload(
    client: TestClient,
    appointment_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
) -> None:
    """Test 12: Missing required reason or blank string returns 422 Unprocessable Entity."""
    appt = appointment_test_env["appointment"]
    assert isinstance(appt, Appointment)

    # 12a. Missing reason field entirely
    res_empty = client.patch(
        f"/api/v1/appointments/{appt.id}/cancel",
        headers=superuser_token_headers,
        json={},
    )
    assert res_empty.status_code == 422

    # 12b. Blank / whitespace-only reason
    res_blank = client.patch(
        f"/api/v1/appointments/{appt.id}/cancel",
        headers=superuser_token_headers,
        json={"reason": "   "},
    )
    assert res_blank.status_code == 422

    # 12c. Invalid type: nested dict / invalid structure
    res_nested = client.patch(
        f"/api/v1/appointments/{appt.id}/cancel",
        headers=superuser_token_headers,
        json={"reason": {"invalid": "object"}},
    )
    assert res_nested.status_code == 422


def test_cancel_appointment_other_customer_forbidden(
    client: TestClient,
    appointment_test_env: dict[str, object],
    db: Session,
) -> None:
    """Test 13: Customer B cannot cancel Customer A's appointment (403 Forbidden)."""
    appt = appointment_test_env["appointment"]
    user_b = appointment_test_env["user_b"]
    assert isinstance(appt, Appointment)
    assert isinstance(user_b, User)

    cust_b_headers = authentication_token_from_email(
        client=client, email=user_b.email, db=db
    )

    response = client.patch(
        f"/api/v1/appointments/{appt.id}/cancel",
        headers=cust_b_headers,
        json={"reason": "Cố hủy lịch người khác"},
    )
    assert response.status_code == 403
    assert "Không đủ quyền" in response.json()["detail"]


def test_cancel_appointment_frees_slot_for_rebooking(
    client: TestClient,
    appointment_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Test 14: Cancelling appointment frees the technician slot immediately for other customers."""
    appt = appointment_test_env["appointment"]
    tech = appointment_test_env["technician"]
    svc = appointment_test_env["service"]
    t_date = appointment_test_env["test_date"]
    cust_b = appointment_test_env["customer_b"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech, Technician)
    assert isinstance(svc, Service)
    assert isinstance(t_date, date)
    assert isinstance(cust_b, Customer)

    # 1. Reset appt to CONFIRMED at 09:00
    appt.status = "CONFIRMED"
    db.add(appt)
    db.commit()

    # 2. Verify slot 09:00 is currently occupied (available = False)
    check_before = client.post(
        "/api/v1/slots/check",
        json={
            "service_id": str(svc.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
            "technician_id": str(tech.id),
        },
    )
    assert check_before.json()["available"] is False

    # 3. Cancel the appointment via PATCH /cancel
    cancel_res = client.patch(
        f"/api/v1/appointments/{appt.id}/cancel",
        headers=superuser_token_headers,
        json={"reason": "Khách hủy để nhường slot"},
    )
    assert cancel_res.status_code == 200

    # 4. Verify slot 09:00 is now free (available = True)
    check_after = client.post(
        "/api/v1/slots/check",
        json={
            "service_id": str(svc.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
            "technician_id": str(tech.id),
        },
    )
    assert check_after.json()["available"] is True

    # 5. Customer B can book this newly freed slot
    rebook_res = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust_b.id),
            "service_id": str(svc.id),
            "appointment_date": t_date.isoformat(),
            "start_time": "09:00",
            "technician_id": str(tech.id),
        },
    )
    assert rebook_res.status_code == 201


def test_database_error_rollback_safety(
    client: TestClient,
    appointment_test_env: dict[str, object],
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Test 15: An unexpected DB commit error triggers rollback and 500 without corrupting state."""
    appt = appointment_test_env["appointment"]
    assert isinstance(appt, Appointment)

    appt.status = "PENDING"
    db.add(appt)
    db.commit()

    # Simulate database failure during commit
    with patch.object(
        Session, "commit", side_effect=RuntimeError("Simulated DB Disk Full")
    ):
        res_confirm = client.patch(
            f"/api/v1/appointments/{appt.id}/confirm",
            headers=superuser_token_headers,
        )
        assert res_confirm.status_code == 500
        assert "Lỗi hệ thống" in res_confirm.json()["detail"]

    # Verify that the appointment status in DB was not left partially committed
    db.expire_all()
    recheck_appt = db.get(Appointment, appt.id)
    assert recheck_appt is not None
    assert recheck_appt.status == "PENDING"
