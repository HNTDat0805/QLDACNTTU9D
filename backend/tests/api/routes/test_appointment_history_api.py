import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.crud import create_user
from app.models import (
    Appointment,
    AppointmentService,
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


def create_history_fixture(db: Session) -> dict[str, object]:
    cust_user = create_role_user(db, "customer")
    customer = Customer(
        full_name="Nguyễn Lịch Sử",
        phone_number=f"084{uuid.uuid4().int % 10000000:07d}",
        user_id=cust_user.id,
    )
    db.add(customer)
    db.commit()

    device = Device(
        customer_id=customer.id,
        brand="Apple",
        model="iPhone 11",
    )
    tech = Technician(
        full_name="Kỹ Thuật Viên Sửa Máy",
        phone_number=f"083{uuid.uuid4().int % 10000000:07d}",
        is_active=True,
    )
    svc = Service(
        name=f"Thay Pin Dung Lượng Cao {uuid.uuid4().hex[:6]}",
        base_price=650_000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    db.add(device)
    db.add(tech)
    db.add(svc)
    db.commit()

    appt_code = f"APPT-HIST-{uuid.uuid4().hex[:6].upper()}"
    appt = Appointment(
        appointment_number=appt_code,
        customer_id=customer.id,
        device_id=device.id,
        technician_id=tech.id,
        appointment_date=datetime.now(UTC) - timedelta(days=5),
        status="COMPLETED",
        customer_notes="Pin bị chai 75%",
        technician_diagnosis="Pin phồng nhẹ, đã thay thế",
        actual_completion_date=datetime.now(UTC) - timedelta(days=5, hours=2),
        total_amount=650_000.0,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    # Link service
    appt_svc = AppointmentService(
        appointment_id=appt.id,
        service_id=svc.id,
        price_at_booking=650_000.0,
        quantity=1,
    )
    db.add(appt_svc)

    # Status history log
    hist1 = RepairStatusHistory(
        appointment_id=appt.id,
        previous_status=None,
        new_status="PENDING",
        note="Khách đặt hẹn",
    )
    hist2 = RepairStatusHistory(
        appointment_id=appt.id,
        previous_status="PENDING",
        new_status="IN_PROGRESS",
        note="Đã tiếp nhận máy",
    )
    hist3 = RepairStatusHistory(
        appointment_id=appt.id,
        previous_status="IN_PROGRESS",
        new_status="COMPLETED",
        note="Sửa xong và kiểm tra",
    )
    db.add(hist1)
    db.add(hist2)
    db.add(hist3)
    db.commit()

    return {
        "customer_user": cust_user,
        "customer": customer,
        "device": device,
        "technician": tech,
        "service": svc,
        "appointment": appt,
    }


def test_read_appointments_history_filtering(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    data = create_history_fixture(db)
    appt = data["appointment"]

    # Filter theo status COMPLETED
    resp = client.get(
        f"{settings.API_V1_STR}/appointments/history?status=COMPLETED&skip=0&limit=10",
        headers=headers,
    )
    assert resp.status_code == 200
    res_json = resp.json()
    assert res_json["count"] >= 1
    found = any(a["id"] == str(appt.id) for a in res_json["data"])
    assert found is True

    # Filter theo từ khóa mã lịch hẹn
    resp_q = client.get(
        f"{settings.API_V1_STR}/appointments/history?q={appt.appointment_number}",
        headers=headers,
    )
    assert resp_q.status_code == 200
    assert resp_q.json()["count"] >= 1
    assert resp_q.json()["data"][0]["appointment_number"] == appt.appointment_number


def test_lookup_appointments_by_number_and_phone(
    client: TestClient, db: Session
) -> None:
    data = create_history_fixture(db)
    appt = data["appointment"]
    cust = data["customer"]

    # Tra cứu bằng appointment_number (công khai / khách tra cứu)
    resp_code = client.get(
        f"{settings.API_V1_STR}/appointments/history/lookup?appointment_number={appt.appointment_number}",
    )
    assert resp_code.status_code == 200
    items = resp_code.json()
    assert len(items) >= 1
    assert items[0]["appointment_number"] == appt.appointment_number

    # Tra cứu bằng phone_number
    resp_phone = client.get(
        f"{settings.API_V1_STR}/appointments/history/lookup?phone_number={cust.phone_number}",
    )
    assert resp_phone.status_code == 200
    assert len(resp_phone.json()) >= 1

    # Thiếu cả 2 param
    resp_empty = client.get(
        f"{settings.API_V1_STR}/appointments/history/lookup",
    )
    assert resp_empty.status_code == 400


def test_read_appointment_detail_full(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    data = create_history_fixture(db)
    appt = data["appointment"]

    response = client.get(
        f"{settings.API_V1_STR}/appointments/{appt.id}/detail",
        headers=headers,
    )
    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == str(appt.id)
    assert detail["status"] == "COMPLETED"
    assert detail["customer"]["full_name"] == data["customer"].full_name
    assert detail["device"]["model"] == "iPhone 11"
    assert detail["technician"]["full_name"] == data["technician"].full_name

    # Services
    assert len(detail["services"]) >= 1
    assert detail["services"][0]["price_at_booking"] == 650_000.0

    # Status history timeline
    assert len(detail["status_history"]) >= 3
    statuses = [h["new_status"] for h in detail["status_history"]]
    assert "PENDING" in statuses
    assert "IN_PROGRESS" in statuses
    assert "COMPLETED" in statuses


def test_customer_appointments_history_endpoint(
    client: TestClient, db: Session
) -> None:
    data = create_history_fixture(db)
    cust_user = data["customer_user"]
    customer = data["customer"]
    other_cust_user = create_role_user(db, "customer")

    # 1. Owner can view own history via /customers/{customer_id}/appointments
    resp_owner = client.get(
        f"{settings.API_V1_STR}/customers/{customer.id}/appointments",
        headers=get_token_headers(cust_user),
    )
    assert resp_owner.status_code == 200
    assert resp_owner.json()["count"] >= 1

    # 2. Other customer is forbidden
    resp_other = client.get(
        f"{settings.API_V1_STR}/customers/{customer.id}/appointments",
        headers=get_token_headers(other_cust_user),
    )
    assert resp_other.status_code == 403


def test_history_rbac(client: TestClient, db: Session) -> None:
    cust_user = create_role_user(db, "customer")
    headers = get_token_headers(cust_user)

    # Customer không được xem toàn bộ lịch sử toàn hệ thống
    response = client.get(
        f"{settings.API_V1_STR}/appointments/history",
        headers=headers,
    )
    assert response.status_code == 403
