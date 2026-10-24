import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.crud import create_user
from app.models import Appointment, Customer, Device, User, UserCreate
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


def test_create_customer_success(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    phone = f"098{uuid.uuid4().int % 10000000:07d}"

    payload = {
        "full_name": "Nguyễn Văn Khách",
        "phone_number": phone,
        "email": random_email(),
        "address": "123 Đường Test, Quận 1",
    }
    response = client.post(
        f"{settings.API_V1_STR}/customers",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Nguyễn Văn Khách"
    assert data["phone_number"] == phone
    assert "id" in data


def test_create_customer_invalid_phone(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)

    payload = {
        "full_name": "Khách Sai SĐT",
        "phone_number": "123",  # < 8 ký tự
    }
    response = client.post(
        f"{settings.API_V1_STR}/customers",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 400
    assert "ít nhất 8 chữ số" in response.json()["detail"]


def test_create_customer_duplicate_phone(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    phone = f"097{uuid.uuid4().int % 10000000:07d}"

    customer = Customer(full_name="Khách Gốc", phone_number=phone)
    db.add(customer)
    db.commit()

    payload = {
        "full_name": "Khách Trùng SĐT",
        "phone_number": phone,
    }
    response = client.post(
        f"{settings.API_V1_STR}/customers",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 409
    assert "đã tồn tại" in response.json()["detail"]


def test_create_customer_nonexistent_user_id(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    phone = f"096{uuid.uuid4().int % 10000000:07d}"

    payload = {
        "full_name": "Khách User Fake",
        "phone_number": phone,
        "user_id": str(uuid.uuid4()),
    }
    response = client.post(
        f"{settings.API_V1_STR}/customers",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 404
    assert "không tồn tại" in response.json()["detail"]


def test_get_customers_pagination_and_search(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)

    unique_code = random_lower_string()[:8]
    cust1 = Customer(
        full_name=f"Tìm Kiếm {unique_code} Alpha",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
    )
    cust2 = Customer(
        full_name=f"Tìm Kiếm {unique_code} Beta",
        phone_number=f"092{uuid.uuid4().int % 10000000:07d}",
    )
    db.add(cust1)
    db.add(cust2)
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/customers?q={unique_code}&skip=0&limit=10",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 2
    assert len(data["data"]) >= 2
    names = [c["full_name"] for c in data["data"]]
    assert any("Alpha" in n for n in names)
    assert any("Beta" in n for n in names)


def test_get_customer_by_id_owner_and_forbidden(
    client: TestClient, db: Session
) -> None:
    cust_user1 = create_role_user(db, "customer")
    cust_user2 = create_role_user(db, "customer")

    customer1 = Customer(
        full_name="Khách Hàng 1",
        phone_number=f"093{uuid.uuid4().int % 10000000:07d}",
        user_id=cust_user1.id,
    )
    db.add(customer1)
    db.commit()
    db.refresh(customer1)

    # 1. Owner customer can view own profile
    resp_owner = client.get(
        f"{settings.API_V1_STR}/customers/{customer1.id}",
        headers=get_token_headers(cust_user1),
    )
    assert resp_owner.status_code == 200
    assert resp_owner.json()["id"] == str(customer1.id)

    # 2. Another customer cannot view customer1's profile
    resp_forbidden = client.get(
        f"{settings.API_V1_STR}/customers/{customer1.id}",
        headers=get_token_headers(cust_user2),
    )
    assert resp_forbidden.status_code == 403

    # 3. Staff can view customer1's profile
    staff = create_role_user(db, "staff")
    resp_staff = client.get(
        f"{settings.API_V1_STR}/customers/{customer1.id}",
        headers=get_token_headers(staff),
    )
    assert resp_staff.status_code == 200


def test_update_customer(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)

    customer = Customer(
        full_name="Khách Cần Đổi Tên",
        phone_number=f"094{uuid.uuid4().int % 10000000:07d}",
        address="Địa chỉ cũ",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    update_payload = {
        "full_name": "Khách Đã Đổi Tên Thành Công",
        "address": "Địa chỉ mới",
    }
    response = client.patch(
        f"{settings.API_V1_STR}/customers/{customer.id}",
        json=update_payload,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Khách Đã Đổi Tên Thành Công"
    assert data["address"] == "Địa chỉ mới"


def test_update_customer_duplicate_phone(client: TestClient, db: Session) -> None:
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)

    phone1 = f"095{uuid.uuid4().int % 10000000:07d}"
    phone2 = f"095{uuid.uuid4().int % 10000000:07d}"

    cust1 = Customer(full_name="Khách A", phone_number=phone1)
    cust2 = Customer(full_name="Khách B", phone_number=phone2)
    db.add(cust1)
    db.add(cust2)
    db.commit()

    # Thử đổi phone của cust2 thành phone1 đã có
    response = client.patch(
        f"{settings.API_V1_STR}/customers/{cust2.id}",
        json={"phone_number": phone1},
        headers=headers,
    )
    assert response.status_code == 409
    assert "đã thuộc về khách hàng khác" in response.json()["detail"]


def test_delete_customer_without_appointments_success(
    client: TestClient, db: Session
) -> None:
    manager = create_role_user(db, "manager")
    headers = get_token_headers(manager)

    customer = Customer(
        full_name="Khách Rảnh Rỗi",
        phone_number=f"099{uuid.uuid4().int % 10000000:07d}",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    response = client.delete(
        f"{settings.API_V1_STR}/customers/{customer.id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert "thành công" in response.json()["message"]

    # Verify not found
    get_resp = client.get(
        f"{settings.API_V1_STR}/customers/{customer.id}",
        headers=headers,
    )
    assert get_resp.status_code == 404


def test_delete_customer_with_appointments_rejected(
    client: TestClient, db: Session
) -> None:
    manager = create_role_user(db, "manager")
    headers = get_token_headers(manager)

    customer = Customer(
        full_name="Khách Có Lịch Sửa Chữa",
        phone_number=f"090{uuid.uuid4().int % 10000000:07d}",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    device = Device(
        customer_id=customer.id,
        device_type="Smartphone",
        brand="Apple",
        model="iPhone 13",
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    appt = Appointment(
        appointment_number=f"APPT-TEST-{uuid.uuid4().hex[:6].upper()}",
        customer_id=customer.id,
        device_id=device.id,
        appointment_date=datetime.now(UTC),
        status="CONFIRMED",
    )
    db.add(appt)
    db.commit()

    response = client.delete(
        f"{settings.API_V1_STR}/customers/{customer.id}",
        headers=headers,
    )
    assert response.status_code == 400
    assert "Không thể xóa khách hàng đã có lịch hẹn" in response.json()["detail"]
