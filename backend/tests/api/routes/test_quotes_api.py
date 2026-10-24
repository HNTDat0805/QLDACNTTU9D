import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import security
from app.crud import create_user
from app.models import (
    Appointment,
    AppointmentStatus,
    Customer,
    Device,
    Quote,
    QuoteItem,
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


def setup_quote_fixture(db: Session) -> dict[str, object]:
    cust = Customer(
        full_name="Lê Minh Khang",
        phone_number=f"092{uuid.uuid4().int % 10000000:07d}",
        email=random_email(),
    )
    db.add(cust)
    db.commit()

    device = Device(
        customer_id=cust.id,
        brand="Apple",
        model="iPhone 14 Pro Max",
        color="Deep Purple",
    )
    db.add(device)

    tech = Technician(
        full_name="Kỹ Thuật Viên Báo Giá",
        phone_number=f"093{uuid.uuid4().int % 10000000:07d}",
        is_active=True,
    )
    db.add(tech)

    svc1 = Service(
        name=f"Thay Màn Hình OLED {uuid.uuid4().hex[:4]}",
        base_price=2_500_000.0,
        estimated_duration_minutes=60,
        is_active=True,
    )
    svc2 = Service(
        name=f"Dán Cường Lực Cao Cấp {uuid.uuid4().hex[:4]}",
        base_price=150_000.0,
        estimated_duration_minutes=15,
        is_active=True,
    )
    db.add(svc1)
    db.add(svc2)
    db.commit()

    appt = Appointment(
        appointment_number=f"APPT-20261024-{uuid.uuid4().hex[:4].upper()}",
        appointment_date=datetime.now(UTC),
        status=AppointmentStatus.IN_PROGRESS.value,
        customer_id=cust.id,
        device_id=device.id,
        technician_id=tech.id,
        customer_notes="Màn hình chảy mực, liệt cảm ứng",
        technician_diagnosis="Cần thay cụm màn hình mới và dán kính bảo vệ",
        total_amount=0.0,
    )
    db.add(appt)
    db.commit()

    return {
        "customer": cust,
        "device": device,
        "technician": tech,
        "service_screen": svc1,
        "service_glass": svc2,
        "appointment": appt,
    }


def test_create_quotation_success_with_multiple_items(
    client: TestClient, db: Session
) -> None:
    """Test tạo báo giá thành công với nhiều hạng mục (từ danh mục dịch vụ và hạng mục tùy biến)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_quote_fixture(db)
    appt = fix["appointment"]
    svc_screen = fix["service_screen"]
    svc_glass = fix["service_glass"]
    assert isinstance(appt, Appointment)
    assert isinstance(svc_screen, Service)
    assert isinstance(svc_glass, Service)

    payload = {
        "appointment_id": str(appt.id),
        "items": [
            {
                "service_id": str(svc_screen.id),
                "quantity": 1,
                "notes": "Màn hình bảo hành 6 tháng",
            },
            {
                "service_id": str(svc_glass.id),
                "quantity": 2,
                "notes": "Dán mặt trước và tặng kèm kính phụ",
            },
            {
                "item_name": "Ốp lưng UAG chống sốc",
                "unit_price": 450_000.0,
                "quantity": 1,
                "notes": "Phụ kiện ngoài danh mục chuẩn",
            },
        ],
        "customer_notes": "Báo giá đã bao gồm công thợ lắp đặt hoàn thiện",
    }

    response = client.post("/api/v1/quotes", json=payload, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "Tạo báo giá sửa chữa" in body["message"]

    data = body["data"]
    assert data["appointment_id"] == str(appt.id)
    assert data["appointment_number"] == appt.appointment_number
    assert data["quote_number"].startswith("QUO-")
    assert data["status"] == "DRAFT"
    assert data["customer_name"] == "Lê Minh Khang"
    assert "iPhone 14 Pro Max" in data["device_info"]

    # Kiểm tra tính toán thành tiền từng item và tổng tiền backend
    # Item 1: 2,500,000 * 1 = 2,500,000
    # Item 2: 150,000 * 2 = 300,000
    # Item 3: 450,000 * 1 = 450,000
    # Tổng: 2,500,000 + 300,000 + 450,000 = 3,250,000.0
    expected_total = 3_250_000.0
    assert data["total_amount"] == expected_total
    assert len(data["items"]) == 3

    items_map = {item["item_name"]: item for item in data["items"]}
    assert svc_screen.name in items_map
    assert items_map[svc_screen.name]["total_price"] == 2_500_000.0

    assert svc_glass.name in items_map
    assert items_map[svc_glass.name]["total_price"] == 300_000.0

    assert "Ốp lưng UAG chống sốc" in items_map
    assert items_map["Ốp lưng UAG chống sốc"]["total_price"] == 450_000.0

    # Kiểm tra lưu vào database
    db.expire_all()
    db_quote = db.get(Quote, uuid.UUID(data["id"]))
    assert db_quote is not None
    assert db_quote.total_amount == expected_total
    assert db_quote.status == "DRAFT"

    db_items = db.exec(
        select(QuoteItem).where(QuoteItem.quote_id == db_quote.id)
    ).all()
    assert len(db_items) == 3


def test_create_quotation_by_appointment_number(
    client: TestClient, db: Session
) -> None:
    """Test tạo báo giá bằng appointment_number thay vì UUID."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_quote_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    payload = {
        "appointment_number": appt.appointment_number,
        "items": [
            {
                "item_name": "Vệ sinh máy và tra keo tản nhiệt",
                "unit_price": 100_000.0,
                "quantity": 1,
            }
        ],
    }

    response = client.post("/api/v1/quotes", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["appointment_id"] == str(appt.id)
    assert data["appointment_number"] == appt.appointment_number
    assert data["total_amount"] == 100_000.0


def test_create_quotation_accurate_decimal_calculation(
    client: TestClient, db: Session
) -> None:
    """Test tính toán tiền tệ chính xác bằng Decimal, tránh sai số số thực."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_quote_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    payload = {
        "appointment_id": str(appt.id),
        "items": [
            {
                "item_name": "Linh kiện A",
                "unit_price": 33.33,
                "quantity": 3,
            },
            {
                "item_name": "Linh kiện B",
                "unit_price": 10.15,
                "quantity": 2,
            },
        ],
    }

    response = client.post("/api/v1/quotes", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()["data"]
    # 33.33 * 3 = 99.99
    # 10.15 * 2 = 20.30
    # Tổng = 99.99 + 20.30 = 120.29
    assert data["total_amount"] == 120.29


def test_create_quotation_empty_items_validation_error(
    client: TestClient, db: Session
) -> None:
    """Test danh sách hạng mục rỗng hoặc dữ liệu không hợp lệ (HTTP 422 hoặc 400)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_quote_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    # 1. Danh sách items rỗng -> 422
    payload_empty = {
        "appointment_id": str(appt.id),
        "items": [],
    }
    res1 = client.post("/api/v1/quotes", json=payload_empty, headers=headers)
    assert res1.status_code == 422

    # 2. Số lượng quantity <= 0 -> 422
    payload_invalid_qty = {
        "appointment_id": str(appt.id),
        "items": [
            {
                "item_name": "Thay pin",
                "unit_price": 300_000.0,
                "quantity": 0,
            }
        ],
    }
    res2 = client.post("/api/v1/quotes", json=payload_invalid_qty, headers=headers)
    assert res2.status_code == 422

    # 3. Đơn giá unit_price < 0 -> 422
    payload_negative_price = {
        "appointment_id": str(appt.id),
        "items": [
            {
                "item_name": "Thay pin",
                "unit_price": -100_000.0,
                "quantity": 1,
            }
        ],
    }
    res3 = client.post(
        "/api/v1/quotes", json=payload_negative_price, headers=headers
    )
    assert res3.status_code == 422

    # 4. Thiếu cả appointment_id lẫn appointment_number -> 422
    payload_no_ref = {
        "items": [
            {
                "item_name": "Thay pin",
                "unit_price": 300_000.0,
                "quantity": 1,
            }
        ],
    }
    res4 = client.post("/api/v1/quotes", json=payload_no_ref, headers=headers)
    assert res4.status_code == 422

    # 5. Hạng mục không có service_id mà thiếu item_name -> 400
    payload_no_name = {
        "appointment_id": str(appt.id),
        "items": [
            {
                "unit_price": 300_000.0,
                "quantity": 1,
            }
        ],
    }
    res5 = client.post("/api/v1/quotes", json=payload_no_name, headers=headers)
    assert res5.status_code == 400
    assert "Cần cung cấp tên hạng mục" in res5.json()["detail"]


def test_create_quotation_appointment_not_found(
    client: TestClient, db: Session
) -> None:
    """Test trả về 404 Not Found khi định danh phiếu sửa chữa không tồn tại."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    random_id = uuid.uuid4()

    # 1. appointment_id không tồn tại
    payload1 = {
        "appointment_id": str(random_id),
        "items": [{"item_name": "Kiểm tra mainboard", "unit_price": 100_000.0}],
    }
    res1 = client.post("/api/v1/quotes", json=payload1, headers=headers)
    assert res1.status_code == 404
    assert "Không tìm thấy phiếu sửa chữa" in res1.json()["detail"]

    # 2. appointment_number không tồn tại
    payload2 = {
        "appointment_number": "APPT-NONEXISTENT-9999",
        "items": [{"item_name": "Kiểm tra mainboard", "unit_price": 100_000.0}],
    }
    res2 = client.post("/api/v1/quotes", json=payload2, headers=headers)
    assert res2.status_code == 404
    assert "Không tìm thấy phiếu sửa chữa" in res2.json()["detail"]


def test_create_quotation_appointment_invalid_status(
    client: TestClient, db: Session
) -> None:
    """Test trả về 409 Conflict khi phiếu sửa chữa đã hủy hoặc đã hoàn thành."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_quote_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    payload = {
        "appointment_id": str(appt.id),
        "items": [{"item_name": "Ép kính màn hình", "unit_price": 350_000.0}],
    }

    # 1. Trạng thái CANCELLED
    appt.status = AppointmentStatus.CANCELLED.value
    db.add(appt)
    db.commit()
    res1 = client.post("/api/v1/quotes", json=payload, headers=headers)
    assert res1.status_code == 409
    assert "đã bị hủy, không thể tạo báo giá" in res1.json()["detail"]

    # 2. Trạng thái COMPLETED
    appt.status = AppointmentStatus.COMPLETED.value
    db.add(appt)
    db.commit()
    res2 = client.post("/api/v1/quotes", json=payload, headers=headers)
    assert res2.status_code == 409
    assert "đã hoàn thành, không thể tạo báo giá mới" in res2.json()["detail"]


def test_create_quotation_service_not_found(
    client: TestClient, db: Session
) -> None:
    """Test trả về 404 Not Found khi chỉ định service_id không tồn tại."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_quote_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    payload = {
        "appointment_id": str(appt.id),
        "items": [
            {
                "service_id": str(uuid.uuid4()),
                "quantity": 1,
            }
        ],
    }
    response = client.post("/api/v1/quotes", json=payload, headers=headers)
    assert response.status_code == 404
    assert "Không tìm thấy dịch vụ sửa chữa" in response.json()["detail"]


def test_create_quotation_rbac_permissions(client: TestClient, db: Session) -> None:
    """Test phân quyền: Chỉ Staff/Tech/Manager/Admin được tạo báo giá, Customer bị 403."""
    fix = setup_quote_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    payload = {
        "appointment_id": str(appt.id),
        "items": [{"item_name": "Thay loa ngoài", "unit_price": 200_000.0}],
    }

    # 1. Khách hàng gọi API -> 403 Forbidden
    cust_user = create_role_user(db, "customer")
    cust_headers = get_token_headers(cust_user)
    res1 = client.post("/api/v1/quotes", json=payload, headers=cust_headers)
    assert res1.status_code == 403

    # 2. Không truyền token -> 401 Unauthorized
    res2 = client.post("/api/v1/quotes", json=payload)
    assert res2.status_code == 401

    # 3. Kỹ thuật viên gọi API -> 201 Created
    tech_user = create_role_user(db, "technician")
    tech_headers = get_token_headers(tech_user)
    res3 = client.post("/api/v1/quotes", json=payload, headers=tech_headers)
    assert res3.status_code == 201


def test_create_quotation_database_error_transaction_rollback(
    client: TestClient, db: Session
) -> None:
    """Test xử lý lỗi ngoại lệ database: session được rollback an toàn và trả về 500."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_quote_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    payload = {
        "appointment_id": str(appt.id),
        "items": [
            {"item_name": "Kiểm tra lỗi nguồn IC", "unit_price": 500_000.0}
        ],
    }

    # Mock generate_quote_number sinh lỗi bất ngờ
    with patch(
        "app.services.quote_service.generate_quote_number",
        side_effect=RuntimeError("Simulated quote generation failure"),
    ):
        response = client.post("/api/v1/quotes", json=payload, headers=headers)
        assert response.status_code == 500
        assert "Đã xảy ra lỗi trong quá trình tạo báo giá sửa chữa" in (
            response.json()["detail"]
        )

    # Đảm bảo rollback sạch sẽ, không có QuoteItem hay Quote nào bị lưu dở dang
    db.expire_all()
    leftover_items = db.exec(
        select(QuoteItem).where(
            QuoteItem.item_name == "Kiểm tra lỗi nguồn IC"
        )
    ).all()
    assert len(leftover_items) == 0
