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
    Invoice,
    Quote,
    QuoteItem,
    QuoteStatus,
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


def setup_repair_fixture(db: Session) -> dict[str, object]:
    cust = Customer(
        full_name="Nguyễn Văn A",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
        email=random_email(),
    )
    db.add(cust)
    db.commit()

    device = Device(
        customer_id=cust.id,
        brand="Apple",
        model="iPhone 13 Pro",
        color="Sierra Blue",
    )
    db.add(device)

    tech = Technician(
        full_name="Kỹ Thuật Viên Tuấn",
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
        is_active=True,
    )
    db.add(tech)

    svc1 = Service(
        name=f"Thay Pin Dung Lượng Cao {uuid.uuid4().hex[:4]}",
        base_price=450_000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    svc2 = Service(
        name=f"Vệ Sinh Máy Chuyên Sâu {uuid.uuid4().hex[:4]}",
        base_price=100_000.0,
        estimated_duration_minutes=20,
        is_active=True,
    )
    db.add(svc1)
    db.add(svc2)
    db.commit()

    appt = Appointment(
        appointment_number=f"APPT-20261101-{uuid.uuid4().hex[:4].upper()}",
        appointment_date=datetime.now(UTC),
        status=AppointmentStatus.IN_PROGRESS.value,
        customer_id=cust.id,
        device_id=device.id,
        technician_id=tech.id,
        customer_notes="Máy nhanh hết pin",
        technician_diagnosis="Pin chai 72%, cần thay pin",
        total_amount=0.0,
    )
    db.add(appt)
    db.commit()

    return {
        "customer": cust,
        "device": device,
        "technician": tech,
        "service_battery": svc1,
        "service_clean": svc2,
        "appointment": appt,
    }


def test_create_invoice_success_from_accepted_quote(
    client: TestClient, db: Session
) -> None:
    """Test tạo hóa đơn thành công từ đơn sửa chữa đã có báo giá ACCEPTED."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    # Tạo báo giá và duyệt ACCEPTED
    quote = Quote(
        quote_number=f"QUO-20261101-{uuid.uuid4().hex[:4].upper()}",
        appointment_id=appt.id,
        status=QuoteStatus.ACCEPTED.value,
        total_amount=550_000.0,
    )
    db.add(quote)
    db.commit()

    item1 = QuoteItem(
        quote_id=quote.id,
        item_name="Thay Pin iPhone 13 Pro",
        unit_price=450_000.0,
        quantity=1,
        total_price=450_000.0,
    )
    item2 = QuoteItem(
        quote_id=quote.id,
        item_name="Dán Ron Chống Nước",
        unit_price=100_000.0,
        quantity=1,
        total_price=100_000.0,
    )
    db.add(item1)
    db.add(item2)
    db.commit()

    # Gọi API tạo hóa đơn
    response = client.post(
        "/api/invoices",
        headers=headers,
        json={"repair_order_id": str(appt.id)},
    )
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["message"] == "Tạo hóa đơn thành công"
    inv = res_data["data"]
    assert inv["repair_order_id"] == str(appt.id)
    assert inv["customer_name"] == "Nguyễn Văn A"
    assert inv["subtotal"] == 550_000.0
    assert inv["total_amount"] == 550_000.0
    assert inv["status"] == "unpaid"
    assert len(inv["items"]) == 2
    assert inv["invoice_code"].startswith("HD-")


def test_create_invoice_success_from_appointment_services(
    client: TestClient, db: Session
) -> None:
    """Test tạo hóa đơn thành công từ các dịch vụ AppointmentService khi không có báo giá."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    svc_battery = fix["service_battery"]
    svc_clean = fix["service_clean"]
    assert isinstance(appt, Appointment)
    assert isinstance(svc_battery, Service)
    assert isinstance(svc_clean, Service)

    appt_svc1 = AppointmentService(
        appointment_id=appt.id,
        service_id=svc_battery.id,
        price_at_booking=450_000.0,
        quantity=1,
    )
    appt_svc2 = AppointmentService(
        appointment_id=appt.id,
        service_id=svc_clean.id,
        price_at_booking=100_000.0,
        quantity=2,
    )
    db.add(appt_svc1)
    db.add(appt_svc2)
    db.commit()

    response = client.post(
        "/api/invoices",
        headers=headers,
        json={"repair_order_id": str(appt.id)},
    )
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["success"] is True
    inv = res_data["data"]
    # 450,000 * 1 + 100,000 * 2 = 650,000
    assert inv["total_amount"] == 650_000.0
    assert inv["status"] == "unpaid"
    assert len(inv["items"]) == 2


def test_create_invoice_repair_order_not_found(client: TestClient, db: Session) -> None:
    """Test tạo hóa đơn thất bại khi đơn sửa chữa không tồn tại (404)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    random_id = str(uuid.uuid4())

    response = client.post(
        "/api/invoices",
        headers=headers,
        json={"repair_order_id": random_id},
    )
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


def test_create_invoice_already_exists_conflict(
    client: TestClient, db: Session
) -> None:
    """Test tạo hóa đơn thất bại khi đơn sửa chữa đã có hóa đơn (409 Conflict)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    svc_battery = fix["service_battery"]
    assert isinstance(appt, Appointment)
    assert isinstance(svc_battery, Service)

    db.add(
        AppointmentService(
            appointment_id=appt.id,
            service_id=svc_battery.id,
            price_at_booking=450_000.0,
            quantity=1,
        )
    )
    db.commit()

    # Lần 1: Tạo thành công
    res1 = client.post(
        "/api/invoices",
        headers=headers,
        json={"repair_order_id": str(appt.id)},
    )
    assert res1.status_code == 201

    # Lần 2: Trùng lặp -> 409 Conflict
    res2 = client.post(
        "/api/invoices",
        headers=headers,
        json={"repair_order_id": str(appt.id)},
    )
    assert res2.status_code == 409
    assert "đã có hóa đơn" in res2.json()["detail"]


def test_create_invoice_cancelled_repair_order(client: TestClient, db: Session) -> None:
    """Test tạo hóa đơn thất bại khi đơn sửa chữa đã bị CANCELLED (400)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)
    appt.status = "CANCELLED"
    db.add(appt)
    db.commit()

    response = client.post(
        "/api/invoices",
        headers=headers,
        json={"repair_order_id": str(appt.id)},
    )
    assert response.status_code == 400
    assert "đã bị hủy" in response.json()["detail"]


def test_create_invoice_no_valid_items(client: TestClient, db: Session) -> None:
    """Test tạo hóa đơn thất bại khi đơn sửa chữa không có hạng mục nào (400)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    response = client.post(
        "/api/invoices",
        headers=headers,
        json={"repair_order_id": str(appt.id)},
    )
    assert response.status_code == 400
    assert "chưa có hạng mục" in response.json()["detail"]


def test_create_invoice_rbac_permissions(client: TestClient, db: Session) -> None:
    """Test kiểm tra phân quyền truy cập API tạo hóa đơn."""
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    svc_battery = fix["service_battery"]
    assert isinstance(appt, Appointment)
    assert isinstance(svc_battery, Service)

    db.add(
        AppointmentService(
            appointment_id=appt.id,
            service_id=svc_battery.id,
            price_at_booking=450_000.0,
            quantity=1,
        )
    )
    db.commit()

    # 1. Chưa đăng nhập -> 401
    res_anon = client.post(
        "/api/invoices",
        json={"repair_order_id": str(appt.id)},
    )
    assert res_anon.status_code == 401

    # 2. Customer -> 403 Forbidden
    cust_user = create_role_user(db, "customer")
    res_cust = client.post(
        "/api/invoices",
        headers=get_token_headers(cust_user),
        json={"repair_order_id": str(appt.id)},
    )
    assert res_cust.status_code == 403

    # 3. Manager -> 201 Created
    manager_user = create_role_user(db, "manager")
    res_mgr = client.post(
        "/api/invoices",
        headers=get_token_headers(manager_user),
        json={"repair_order_id": str(appt.id)},
    )
    assert res_mgr.status_code == 201


def test_get_invoice_detail_and_list(client: TestClient, db: Session) -> None:
    """Test truy vấn chi tiết hóa đơn và danh sách hóa đơn."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    svc_clean = fix["service_clean"]
    assert isinstance(appt, Appointment)
    assert isinstance(svc_clean, Service)

    db.add(
        AppointmentService(
            appointment_id=appt.id,
            service_id=svc_clean.id,
            price_at_booking=100_000.0,
            quantity=1,
        )
    )
    db.commit()

    res_create = client.post(
        "/api/invoices",
        headers=headers,
        json={"repair_order_id": str(appt.id)},
    )
    assert res_create.status_code == 201
    inv_id = res_create.json()["data"]["id"]

    # Get by ID
    res_get = client.get(f"/api/invoices/{inv_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["data"]["id"] == inv_id

    # List invoices
    res_list = client.get("/api/invoices", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json()["count"] >= 1


def test_create_invoice_database_rollback_on_error(
    client: TestClient, db: Session
) -> None:
    """Test giao dịch cơ sở dữ liệu rollback an toàn khi phát sinh lỗi bất ngờ."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    svc_clean = fix["service_clean"]
    assert isinstance(appt, Appointment)
    assert isinstance(svc_clean, Service)

    db.add(
        AppointmentService(
            appointment_id=appt.id,
            service_id=svc_clean.id,
            price_at_booking=100_000.0,
            quantity=1,
        )
    )
    db.commit()

    with patch.object(
        Session, "commit", side_effect=RuntimeError("Lỗi kết nối database giả lập")
    ):
        response = client.post(
            "/api/invoices",
            headers=headers,
            json={"repair_order_id": str(appt.id)},
        )
        assert response.status_code == 500

    # Đảm bảo không có hóa đơn rác nào được commit
    invoices = db.exec(select(Invoice).where(Invoice.appointment_id == appt.id)).all()
    assert len(invoices) == 0
