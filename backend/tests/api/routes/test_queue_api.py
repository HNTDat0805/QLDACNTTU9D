import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.crud import create_user
from app.models import (
    Appointment,
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


def create_queue_fixture(db: Session) -> dict[str, object]:
    cust = Customer(
        full_name="Khách Hàng Hàng Chờ",
        phone_number=f"086{uuid.uuid4().int % 10000000:07d}",
    )
    db.add(cust)
    db.commit()

    device = Device(
        customer_id=cust.id,
        brand="Apple",
        model="iPhone 12 Pro",
    )
    db.add(device)

    tech = Technician(
        full_name="Thợ Chính Hàng Chờ",
        phone_number=f"085{uuid.uuid4().int % 10000000:07d}",
        is_active=True,
    )
    db.add(tech)

    svc = Service(
        name=f"Dịch Vụ Hàng Chờ {uuid.uuid4().hex[:6]}",
        base_price=500_000.0,
        estimated_duration_minutes=45,
        is_active=True,
    )
    db.add(svc)
    db.commit()

    return {
        "customer": cust,
        "device": device,
        "technician": tech,
        "service": svc,
    }


def test_read_queue_list_and_ordering(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    data = create_queue_fixture(db)
    cust = data["customer"]
    device = data["device"]
    tech = data["technician"]

    today = date.today()
    dt1 = datetime.combine(today, time(9, 0), tzinfo=UTC)
    dt2 = datetime.combine(today, time(10, 0), tzinfo=UTC)
    dt3 = datetime.combine(today, time(11, 0), tzinfo=UTC)

    # Tạo 3 lịch hẹn: 2 cái CONFIRMED/IN_PROGRESS (trong queue), 1 cái COMPLETED (ngoài queue)
    appt1 = Appointment(
        appointment_number=f"APPT-Q1-{uuid.uuid4().hex[:6].upper()}",
        customer_id=cust.id,
        device_id=device.id,
        technician_id=tech.id,
        appointment_date=dt2,
        status="CONFIRMED",
    )
    appt2 = Appointment(
        appointment_number=f"APPT-Q2-{uuid.uuid4().hex[:6].upper()}",
        customer_id=cust.id,
        device_id=device.id,
        technician_id=tech.id,
        appointment_date=dt1,
        status="IN_PROGRESS",
    )
    appt_completed = Appointment(
        appointment_number=f"APPT-QC-{uuid.uuid4().hex[:6].upper()}",
        customer_id=cust.id,
        device_id=device.id,
        technician_id=tech.id,
        appointment_date=dt3,
        status="COMPLETED",
    )
    db.add(appt1)
    db.add(appt2)
    db.add(appt_completed)
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/queue?date={today}",
        headers=headers,
    )
    assert response.status_code == 200
    res_data = response.json()

    # Kiểm tra chỉ có appt1 và appt2 trong kết quả lọc ngày hôm nay (appt_completed bị loại)
    appt_numbers = [item["appointment_number"] for item in res_data["data"]]
    assert appt1.appointment_number in appt_numbers
    assert appt2.appointment_number in appt_numbers
    assert appt_completed.appointment_number not in appt_numbers

    # Kiểm tra thứ tự ưu tiên: dt1 (09:00) phải xếp trước dt2 (10:00)
    idx_appt2 = appt_numbers.index(appt2.appointment_number)
    idx_appt1 = appt_numbers.index(appt1.appointment_number)
    assert idx_appt2 < idx_appt1
    assert res_data["data"][idx_appt2]["queue_position"] == idx_appt2 + 1


def test_read_queue_item_detail(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    data = create_queue_fixture(db)

    appt = Appointment(
        appointment_number=f"APPT-QDET-{uuid.uuid4().hex[:6].upper()}",
        customer_id=data["customer"].id,
        device_id=data["device"].id,
        technician_id=data["technician"].id,
        appointment_date=datetime.now(UTC) + timedelta(hours=2),
        status="PENDING",
        customer_notes="Màn hình bị chớp",
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    response = client.get(
        f"{settings.API_V1_STR}/queue/{appt.id}",
        headers=headers,
    )
    assert response.status_code == 200
    item = response.json()
    assert item["appointment_id"] == str(appt.id)
    assert item["customer_name"] == data["customer"].full_name
    assert item["customer_notes"] == "Màn hình bị chớp"
    assert item["queue_position"] >= 1


def test_read_queue_item_not_in_active_queue(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    data = create_queue_fixture(db)

    appt = Appointment(
        appointment_number=f"APPT-QCANCEL-{uuid.uuid4().hex[:6].upper()}",
        customer_id=data["customer"].id,
        device_id=data["device"].id,
        appointment_date=datetime.now(UTC),
        status="CANCELLED",
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    response = client.get(
        f"{settings.API_V1_STR}/queue/{appt.id}",
        headers=headers,
    )
    assert response.status_code == 404
    assert "hàng chờ hoạt động" in response.json()["detail"]


def test_update_queue_status_progression_and_audit(
    client: TestClient, db: Session
) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    data = create_queue_fixture(db)

    appt = Appointment(
        appointment_number=f"APPT-QPROG-{uuid.uuid4().hex[:6].upper()}",
        customer_id=data["customer"].id,
        device_id=data["device"].id,
        technician_id=data["technician"].id,
        appointment_date=datetime.now(UTC),
        status="PENDING",
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    # 1. PENDING -> CONFIRMED
    resp_conf = client.patch(
        f"{settings.API_V1_STR}/queue/{appt.id}/status",
        json={"status": "CONFIRMED", "note": "Tiếp nhận máy tại quầy"},
        headers=headers,
    )
    assert resp_conf.status_code == 200
    assert resp_conf.json()["status"] == "CONFIRMED"

    # 2. CONFIRMED -> IN_PROGRESS
    resp_prog = client.patch(
        f"{settings.API_V1_STR}/queue/{appt.id}/status",
        json={
            "status": "IN_PROGRESS",
            "technician_diagnosis": "Lỗi cáp màn hình",
            "note": "Bắt đầu tháo máy kiểm tra",
        },
        headers=headers,
    )
    assert resp_prog.status_code == 200
    assert resp_prog.json()["status"] == "IN_PROGRESS"
    assert resp_prog.json()["technician_diagnosis"] == "Lỗi cáp màn hình"

    # 3. IN_PROGRESS -> COMPLETED
    resp_comp = client.patch(
        f"{settings.API_V1_STR}/queue/{appt.id}/status",
        json={"status": "COMPLETED", "note": "Thay thế cáp thành công, bàn giao khách"},
        headers=headers,
    )
    assert resp_comp.status_code == 200
    assert resp_comp.json()["status"] == "COMPLETED"

    # 4. Kiểm tra audit trail trong RepairStatusHistory
    histories = db.exec(
        select(RepairStatusHistory)
        .where(RepairStatusHistory.appointment_id == appt.id)
        .order_by(RepairStatusHistory.created_at.asc())
    ).all()
    assert len(histories) >= 3
    notes = [h.note for h in histories]
    assert any("Tiếp nhận máy" in n for n in notes if n)
    assert any("Bắt đầu tháo máy" in n for n in notes if n)
    assert any("Thay thế cáp thành công" in n for n in notes if n)

    # 5. Thử cập nhật tiếp sau khi COMPLETED -> 409 Conflict
    resp_conflict = client.patch(
        f"{settings.API_V1_STR}/queue/{appt.id}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert resp_conflict.status_code == 409
    assert "đã kết thúc" in resp_conflict.json()["detail"]


def test_queue_rbac(client: TestClient, db: Session) -> None:
    customer_user = create_role_user(db, "customer")
    headers = get_token_headers(customer_user)

    # Customer không được xem hàng chờ kỹ thuật
    response = client.get(
        f"{settings.API_V1_STR}/queue",
        headers=headers,
    )
    assert response.status_code == 403
