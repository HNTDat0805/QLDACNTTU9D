import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import security
from app.crud import create_user
from app.models import Customer, Device, User, UserCreate
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


def setup_device_fixture(db: Session) -> dict[str, object]:
    cust = Customer(
        full_name="Hoàng Nam",
        phone_number=f"096{uuid.uuid4().int % 10000000:07d}",
        email=random_email(),
    )
    db.add(cust)
    db.commit()

    device = Device(
        customer_id=cust.id,
        brand="Apple",
        model="iPhone 12 Pro",
        color="Pacific Blue",
        imei="356789012345678",
        serial_number="DNPZ12345678",
        notes="Vỏ trầy xước viền",
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    return {"customer": cust, "device": device}


def test_update_device_success(client: TestClient, db: Session) -> None:
    """Test cập nhật thành công thông tin thiết bị (Update Device)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_device_fixture(db)
    dev = fix["device"]
    assert isinstance(dev, Device)

    payload = {
        "color": "Midnight Black",
        "notes": "Đã thay sườn mới, ngoại quan hoàn thiện",
    }

    response = client.patch(f"/api/v1/devices/{dev.id}", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Cập nhật thông tin thiết bị" in body["message"]

    data = body["data"]
    assert data["id"] == str(dev.id)
    assert data["color"] == "Midnight Black"
    assert data["notes"] == "Đã thay sườn mới, ngoại quan hoàn thiện"
    # Các trường không gửi không bị xóa hoặc ghi đè
    assert data["brand"] == "Apple"
    assert data["model"] == "iPhone 12 Pro"
    assert data["imei"] == "356789012345678"

    # Kiểm tra database thực tế
    db.expire_all()
    db_dev = db.get(Device, dev.id)
    assert db_dev is not None
    assert db_dev.color == "Midnight Black"
    assert db_dev.notes == "Đã thay sườn mới, ngoại quan hoàn thiện"
    assert db_dev.updated_at is not None


def test_update_device_not_found(client: TestClient, db: Session) -> None:
    """Test cập nhật thiết bị với ID không tồn tại -> 404 Not Found."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    random_id = uuid.uuid4()

    response = client.patch(
        f"/api/v1/devices/{random_id}",
        json={"color": "Gold"},
        headers=headers,
    )
    assert response.status_code == 404
    assert "Không tìm thấy thiết bị" in response.json()["detail"]


def test_update_device_does_not_modify_restricted_fields(
    client: TestClient, db: Session
) -> None:
    """Test không cho phép thay đổi ID hoặc customer_id ngoài phạm vi."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_device_fixture(db)
    dev = fix["device"]
    cust = fix["customer"]
    assert isinstance(dev, Device)
    assert isinstance(cust, Customer)

    fake_id = str(uuid.uuid4())
    fake_customer_id = str(uuid.uuid4())
    payload = {
        "id": fake_id,
        "customer_id": fake_customer_id,
        "model": "iPhone 12 Pro Max",
    }

    response = client.patch(f"/api/v1/devices/{dev.id}", json=payload, headers=headers)
    assert response.status_code == 200

    db.expire_all()
    db_dev = db.get(Device, dev.id)
    assert db_dev is not None
    assert db_dev.id == dev.id  # ID không bị thay đổi
    assert db_dev.customer_id == cust.id  # customer_id không bị thay đổi
    assert db_dev.model == "iPhone 12 Pro Max"  # model được cập nhật hợp lệ


def test_update_device_rbac_customer_owner_success(
    client: TestClient, db: Session
) -> None:
    """Test khách hàng chủ sở hữu thiết bị được phép cập nhật thiết bị của mình."""
    cust_user = create_role_user(db, "customer")
    cust_headers = get_token_headers(cust_user)

    cust = Customer(
        user_id=cust_user.id,
        full_name="Khách Hàng Sở Hữu Máy",
        phone_number=f"097{uuid.uuid4().int % 10000000:07d}",
        email=cust_user.email,
    )
    db.add(cust)
    db.commit()

    dev = Device(
        customer_id=cust.id,
        brand="Samsung",
        model="Galaxy S21",
        color="Gray",
    )
    db.add(dev)
    db.commit()

    response = client.patch(
        f"/api/v1/devices/{dev.id}",
        json={"color": "Phantom Violet"},
        headers=cust_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["color"] == "Phantom Violet"


def test_update_device_rbac_customer_forbidden_other_device(
    client: TestClient, db: Session
) -> None:
    """Test khách hàng B không có quyền sửa thiết bị của khách hàng A (403 Forbidden)."""
    # Khách hàng A
    cust_user_a = create_role_user(db, "customer")
    cust_a = Customer(
        user_id=cust_user_a.id,
        full_name="Khách Hàng A",
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
    )
    db.add(cust_a)
    db.commit()

    dev_a = Device(
        customer_id=cust_a.id,
        brand="Xiaomi",
        model="Mi 11",
    )
    db.add(dev_a)
    db.commit()

    # Khách hàng B cố gắng cập nhật thiết bị của A
    cust_user_b = create_role_user(db, "customer")
    cust_b_headers = get_token_headers(cust_user_b)

    response = client.patch(
        f"/api/v1/devices/{dev_a.id}",
        json={"color": "Red"},
        headers=cust_b_headers,
    )
    assert response.status_code == 403
    assert "Bạn không có quyền cập nhật" in response.json()["detail"]


def test_update_device_unauthorized_no_token(client: TestClient) -> None:
    """Test gọi API không có token -> 401 Unauthorized."""
    random_id = uuid.uuid4()
    response = client.patch(f"/api/v1/devices/{random_id}", json={"color": "Silver"})
    assert response.status_code == 401


def test_update_device_alias_endpoint(client: TestClient, db: Session) -> None:
    """Test gọi qua alias /api/devices/{device_id} hoạt động tương đương /api/v1/devices/{device_id}."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_device_fixture(db)
    dev = fix["device"]
    assert isinstance(dev, Device)

    response = client.patch(
        f"/api/devices/{dev.id}",
        json={"color": "Graphite Black", "notes": "Đã đổi qua alias"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["color"] == "Graphite Black"
