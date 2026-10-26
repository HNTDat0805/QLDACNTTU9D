import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.crud import create_user
from app.models import Appointment, Customer, Device, Technician, User, UserCreate
from tests.utils.utils import random_email, random_lower_string


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


def test_create_technician_success(client: TestClient, db: Session) -> None:
    manager = create_role_user(db, "manager")
    headers = get_token_headers(manager)
    phone = f"091{uuid.uuid4().int % 10000000:07d}"

    payload = {
        "full_name": "Kỹ Thuật Viên Giỏi",
        "phone_number": phone,
        "specialization": "Màn hình, Ép kính",
        "is_active": True,
    }
    response = client.post(
        f"{settings.API_V1_STR}/technicians",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Kỹ Thuật Viên Giỏi"
    assert data["phone_number"] == phone
    assert data["specialization"] == "Màn hình, Ép kính"
    assert data["is_active"] is True
    assert "id" in data


def test_create_technician_duplicate_phone(client: TestClient, db: Session) -> None:
    manager = create_role_user(db, "manager")
    headers = get_token_headers(manager)
    phone = f"091{uuid.uuid4().int % 10000000:07d}"

    tech = Technician(full_name="Tech Gốc", phone_number=phone)
    db.add(tech)
    db.commit()

    payload = {
        "full_name": "Tech Trùng SĐT",
        "phone_number": phone,
    }
    response = client.post(
        f"{settings.API_V1_STR}/technicians",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 409
    assert "đã tồn tại" in response.json()["detail"]


def test_create_technician_invalid_user_id(client: TestClient, db: Session) -> None:
    manager = create_role_user(db, "manager")
    headers = get_token_headers(manager)

    payload = {
        "full_name": "Tech User Ảo",
        "phone_number": f"091{uuid.uuid4().int % 10000000:07d}",
        "user_id": str(uuid.uuid4()),
    }
    response = client.post(
        f"{settings.API_V1_STR}/technicians",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 404
    assert "không tồn tại" in response.json()["detail"]


def test_get_technicians_filter_and_search(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)

    tag = random_lower_string()[:6]
    tech1 = Technician(
        full_name=f"Võ Văn {tag}",
        phone_number=f"092{uuid.uuid4().int % 10000000:07d}",
        specialization=f"Phần cứng {tag}",
        is_active=True,
    )
    tech2 = Technician(
        full_name=f"Lý Văn {tag}",
        phone_number=f"093{uuid.uuid4().int % 10000000:07d}",
        specialization=f"Phần mềm {tag}",
        is_active=False,
    )
    db.add(tech1)
    db.add(tech2)
    db.commit()

    # Lọc theo chuyên môn
    resp_spec = client.get(
        f"{settings.API_V1_STR}/technicians?specialization=Phần cứng {tag}",
        headers=headers,
    )
    assert resp_spec.status_code == 200
    assert resp_spec.json()["count"] >= 1
    assert any(t["full_name"] == f"Võ Văn {tag}" for t in resp_spec.json()["data"])

    # Lọc theo is_active
    resp_active = client.get(
        f"{settings.API_V1_STR}/technicians?q={tag}&is_active=false",
        headers=headers,
    )
    assert resp_active.status_code == 200
    assert all(t["is_active"] is False for t in resp_active.json()["data"])


def test_get_technician_by_id(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)

    tech = Technician(
        full_name="Nguyễn Kỹ Thuật",
        phone_number=f"094{uuid.uuid4().int % 10000000:07d}",
    )
    db.add(tech)
    db.commit()
    db.refresh(tech)

    response = client.get(
        f"{settings.API_V1_STR}/technicians/{tech.id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(tech.id)

    # Not found
    resp_not_found = client.get(
        f"{settings.API_V1_STR}/technicians/{uuid.uuid4()}",
        headers=headers,
    )
    assert resp_not_found.status_code == 404


def test_update_technician(client: TestClient, db: Session) -> None:
    manager = create_role_user(db, "manager")
    headers = get_token_headers(manager)

    tech = Technician(
        full_name="Kỹ Thuật Cần Sửa",
        phone_number=f"095{uuid.uuid4().int % 10000000:07d}",
        specialization="Cũ",
    )
    db.add(tech)
    db.commit()
    db.refresh(tech)

    response = client.patch(
        f"{settings.API_V1_STR}/technicians/{tech.id}",
        json={"full_name": "Kỹ Thuật Đã Sửa", "specialization": "Chuyên gia Bo mạch"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Kỹ Thuật Đã Sửa"
    assert data["specialization"] == "Chuyên gia Bo mạch"


def test_update_technician_status(client: TestClient, db: Session) -> None:
    manager = create_role_user(db, "manager")
    headers = get_token_headers(manager)

    tech = Technician(
        full_name="Kỹ Thuật Nghỉ Phép",
        phone_number=f"096{uuid.uuid4().int % 10000000:07d}",
        is_active=True,
    )
    db.add(tech)
    db.commit()
    db.refresh(tech)

    # Đổi sang nghỉ phép (is_active=False)
    resp_off = client.patch(
        f"{settings.API_V1_STR}/technicians/{tech.id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert resp_off.status_code == 200
    assert resp_off.json()["is_active"] is False

    # Kích hoạt lại (is_active=True)
    resp_on = client.patch(
        f"{settings.API_V1_STR}/technicians/{tech.id}/status",
        json={"is_active": True},
        headers=headers,
    )
    assert resp_on.status_code == 200
    assert resp_on.json()["is_active"] is True


def test_delete_technician_success(client: TestClient, db: Session) -> None:
    admin = create_role_user(db, "admin")
    headers = get_token_headers(admin)

    tech = Technician(
        full_name="Kỹ Thuật Thử Việc",
        phone_number=f"097{uuid.uuid4().int % 10000000:07d}",
    )
    db.add(tech)
    db.commit()
    db.refresh(tech)

    response = client.delete(
        f"{settings.API_V1_STR}/technicians/{tech.id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert "thành công" in response.json()["message"]


def test_delete_technician_with_appointment_rejected(
    client: TestClient, db: Session
) -> None:
    admin = create_role_user(db, "admin")
    headers = get_token_headers(admin)

    customer = Customer(
        full_name="Khách Hàng Tech Test",
        phone_number=f"081{uuid.uuid4().int % 10000000:07d}",
    )
    tech = Technician(
        full_name="Tech Bị Ràng Buộc",
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
    )
    db.add(customer)
    db.add(tech)
    db.commit()

    device = Device(customer_id=customer.id, brand="Samsung", model="S23")
    db.add(device)
    db.commit()

    appt = Appointment(
        appointment_number=f"APPT-TECH-{uuid.uuid4().hex[:6].upper()}",
        customer_id=customer.id,
        device_id=device.id,
        technician_id=tech.id,
        appointment_date=datetime.now(UTC),
        status="IN_PROGRESS",
    )
    db.add(appt)
    db.commit()

    response = client.delete(
        f"{settings.API_V1_STR}/technicians/{tech.id}",
        headers=headers,
    )
    assert response.status_code == 400
    assert (
        "Không thể xóa kỹ thuật viên đã được liên kết với lịch hẹn"
        in response.json()["detail"]
    )


def test_technicians_rbac(client: TestClient, db: Session) -> None:
    customer_user = create_role_user(db, "customer")
    headers = get_token_headers(customer_user)

    # Customer không được tạo hoặc xóa kỹ thuật viên
    resp_create = client.post(
        f"{settings.API_V1_STR}/technicians",
        json={"full_name": "Tech Hacked", "phone_number": "0999999999"},
        headers=headers,
    )
    assert resp_create.status_code == 403

    resp_delete = client.delete(
        f"{settings.API_V1_STR}/technicians/{uuid.uuid4()}",
        headers=headers,
    )
    assert resp_delete.status_code == 403
