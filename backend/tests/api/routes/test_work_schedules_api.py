import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.crud import create_user
from app.models import (
    Appointment,
    Customer,
    Device,
    Technician,
    TechnicianSchedule,
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


def create_test_tech(db: Session, is_active: bool = True) -> Technician:
    tech = Technician(
        full_name=f"Tech Schedule Test {uuid.uuid4().hex[:4]}",
        phone_number=f"088{uuid.uuid4().int % 10000000:07d}",
        is_active=is_active,
    )
    db.add(tech)
    db.commit()
    db.refresh(tech)
    return tech


def test_create_work_schedule_success(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    tech = create_test_tech(db)
    target_date = date.today() + timedelta(days=20)

    payload = {
        "technician_id": str(tech.id),
        "work_date": str(target_date),
        "start_time": "08:00:00",
        "end_time": "12:00:00",
        "status": "AVAILABLE",
        "notes": "Ca sáng",
    }
    response = client.post(
        f"{settings.API_V1_STR}/work-schedules",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["technician_id"] == str(tech.id)
    assert data["start_time"] == "08:00:00"
    assert data["end_time"] == "12:00:00"
    assert data["status"] == "AVAILABLE"


def test_create_work_schedule_invalid_time(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    tech = create_test_tech(db)
    target_date = date.today() + timedelta(days=21)

    # Giờ kết thúc trước giờ bắt đầu
    payload = {
        "technician_id": str(tech.id),
        "work_date": str(target_date),
        "start_time": "14:00:00",
        "end_time": "10:00:00",
    }
    response = client.post(
        f"{settings.API_V1_STR}/work-schedules",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 400
    assert "sau giờ bắt đầu" in response.json()["detail"]


def test_create_work_schedule_overlap_conflict(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    tech = create_test_tech(db)
    target_date = date.today() + timedelta(days=22)

    # Ca 1: 08:00 - 12:00
    sch1 = TechnicianSchedule(
        technician_id=tech.id,
        work_date=target_date,
        start_time=time(8, 0),
        end_time=time(12, 0),
        status="AVAILABLE",
    )
    db.add(sch1)
    db.commit()

    # Thử tạo Ca 2: 10:00 - 14:00 (trùng 10:00 - 12:00)
    payload = {
        "technician_id": str(tech.id),
        "work_date": str(target_date),
        "start_time": "10:00:00",
        "end_time": "14:00:00",
    }
    response = client.post(
        f"{settings.API_V1_STR}/work-schedules",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 409
    assert "trùng lặp" in response.json()["detail"]


def test_get_work_schedules_filtering(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    tech = create_test_tech(db)
    target_date = date.today() + timedelta(days=25)

    sch = TechnicianSchedule(
        technician_id=tech.id,
        work_date=target_date,
        start_time=time(13, 0),
        end_time=time(17, 0),
        status="AVAILABLE",
    )
    db.add(sch)
    db.commit()

    # Filter theo tech và ngày
    response = client.get(
        f"{settings.API_V1_STR}/work-schedules?technician_id={tech.id}&work_date={target_date}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert data["data"][0]["technician_id"] == str(tech.id)


def test_get_work_schedule_by_id(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    tech = create_test_tech(db)

    sch = TechnicianSchedule(
        technician_id=tech.id,
        work_date=date.today() + timedelta(days=26),
        start_time=time(8, 30),
        end_time=time(11, 30),
    )
    db.add(sch)
    db.commit()
    db.refresh(sch)

    response = client.get(
        f"{settings.API_V1_STR}/work-schedules/{sch.id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(sch.id)


def test_update_work_schedule_with_appointment_conflict(
    client: TestClient, db: Session
) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    tech = create_test_tech(db)
    target_date = date.today() + timedelta(days=30)

    # 1. Ca làm việc 08:00 - 12:00
    sch = TechnicianSchedule(
        technician_id=tech.id,
        work_date=target_date,
        start_time=time(8, 0),
        end_time=time(12, 0),
        status="AVAILABLE",
    )
    db.add(sch)

    # 2. Lịch hẹn vào lúc 09:00 cùng ngày của kỹ thuật viên
    customer = Customer(
        full_name="Khách Xung Đột", phone_number=f"087{uuid.uuid4().int % 10000000:07d}"
    )
    db.add(customer)
    db.commit()

    device = Device(customer_id=customer.id, brand="Xiaomi", model="Redmi Note 12")
    db.add(device)
    db.commit()

    appt_dt = datetime.combine(target_date, time(9, 0), tzinfo=UTC)
    appt = Appointment(
        appointment_number=f"APPT-SCH-{uuid.uuid4().hex[:6].upper()}",
        customer_id=customer.id,
        device_id=device.id,
        technician_id=tech.id,
        appointment_date=appt_dt,
        status="CONFIRMED",
    )
    db.add(appt)
    db.commit()
    db.refresh(sch)

    # 3. Thử chuyển trạng thái ca sang OFF -> Phải bị từ chối 409
    resp_off = client.patch(
        f"{settings.API_V1_STR}/work-schedules/{sch.id}/status",
        json={"status": "OFF"},
        headers=headers,
    )
    assert resp_off.status_code == 409
    assert (
        "đã có" in resp_off.json()["detail"] or "lịch hẹn" in resp_off.json()["detail"]
    )

    # 4. Thử xóa ca làm việc -> Phải bị từ chối 409
    manager = create_role_user(db, "manager")
    resp_del = client.delete(
        f"{settings.API_V1_STR}/work-schedules/{sch.id}",
        headers=get_token_headers(manager),
    )
    assert resp_del.status_code == 409
    assert "lịch hẹn" in resp_del.json()["detail"]


def test_delete_work_schedule_success(client: TestClient, db: Session) -> None:
    manager = create_role_user(db, "manager")
    headers = get_token_headers(manager)
    tech = create_test_tech(db)

    sch = TechnicianSchedule(
        technician_id=tech.id,
        work_date=date.today() + timedelta(days=35),
        start_time=time(13, 0),
        end_time=time(16, 0),
        status="AVAILABLE",
    )
    db.add(sch)
    db.commit()
    db.refresh(sch)

    response = client.delete(
        f"{settings.API_V1_STR}/work-schedules/{sch.id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert "thành công" in response.json()["message"]


def test_work_schedules_rbac(client: TestClient, db: Session) -> None:
    customer_user = create_role_user(db, "customer")
    headers = get_token_headers(customer_user)

    # Customer không được xem hoặc tạo lịch làm việc
    resp_get = client.get(
        f"{settings.API_V1_STR}/work-schedules",
        headers=headers,
    )
    assert resp_get.status_code == 403

    resp_create = client.post(
        f"{settings.API_V1_STR}/work-schedules",
        json={"technician_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert resp_create.status_code == 403
