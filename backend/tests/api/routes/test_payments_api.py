import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import security
from app.crud import create_user
from app.models import (
    Appointment,
    Customer,
    Device,
    Invoice,
    InvoiceItem,
    Payment,
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


def setup_invoice_fixture(
    db: Session, total_amount: float = 500_000.0, status: str = "unpaid"
) -> dict[str, object]:
    cust = Customer(
        full_name="Trần Thị B",
        phone_number=f"097{uuid.uuid4().int % 10000000:07d}",
        email=random_email(),
    )
    db.add(cust)
    db.commit()

    device = Device(
        customer_id=cust.id,
        brand="Samsung",
        model="Galaxy S22",
        color="Phantom Black",
    )
    db.add(device)

    tech = Technician(
        full_name="Kỹ Thuật Viên Minh",
        phone_number=f"096{uuid.uuid4().int % 10000000:07d}",
        is_active=True,
    )
    db.add(tech)
    db.commit()

    appt = Appointment(
        appointment_number=f"APPT-20261101-{uuid.uuid4().hex[:4].upper()}",
        appointment_date=datetime.now(UTC),
        status="IN_PROGRESS",
        customer_id=cust.id,
        device_id=device.id,
        technician_id=tech.id,
        total_amount=total_amount,
    )
    db.add(appt)
    db.commit()

    inv = Invoice(
        invoice_number=f"HD-20261101-{uuid.uuid4().hex[:4].upper()}",
        appointment_id=appt.id,
        customer_id=cust.id,
        subtotal=total_amount,
        discount_amount=0.0,
        tax_amount=0.0,
        total_amount=total_amount,
        status=status,
        issue_date=datetime.now(UTC),
        notes="Hóa đơn test thanh toán",
    )
    db.add(inv)
    db.commit()

    item = InvoiceItem(
        invoice_id=inv.id,
        item_name="Thay Cụm Chân Sạc Type-C",
        unit_price=total_amount,
        quantity=1,
        total_price=total_amount,
    )
    db.add(item)
    db.commit()

    return {
        "customer": cust,
        "device": device,
        "technician": tech,
        "appointment": appt,
        "invoice": inv,
    }


def test_record_payment_full_success(client: TestClient, db: Session) -> None:
    """Test ghi nhận thanh toán toàn bộ thành công (unpaid -> paid)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db, total_amount=500_000.0)
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    response = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 500_000.0,
            "payment_method": "cash",
            "transaction_code": None,
            "note": "Khách thanh toán tiền mặt tại quầy đầy đủ",
        },
    )
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["message"] == "Ghi nhận thanh toán thành công"
    payment_info = res_data["data"]
    assert payment_info["invoice_id"] == str(inv.id)
    assert payment_info["amount"] == 500_000.0
    assert payment_info["payment_method"] == "cash"
    assert payment_info["status"] == "completed"
    assert payment_info["invoice_status_after_payment"] == "paid"
    assert payment_info["invoice_remaining_amount"] == 0.0
    assert payment_info["payment_code"].startswith("PAY-")

    # Kiểm tra hóa đơn trong database đã đổi sang paid
    db.refresh(inv)
    assert inv.status == "paid"


def test_record_payment_partial_success(client: TestClient, db: Session) -> None:
    """Test ghi nhận thanh toán một phần (unpaid -> partially_paid)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db, total_amount=500_000.0)
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    response = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 200_000.0,
            "payment_method": "cash",
            "transaction_code": None,
            "note": "Khách đặt cọc trước một phần",
        },
    )
    assert response.status_code == 201
    res_data = response.json()
    payment_info = res_data["data"]
    assert payment_info["amount"] == 200_000.0
    assert payment_info["invoice_status_after_payment"] == "partially_paid"
    assert payment_info["invoice_remaining_amount"] == 300_000.0

    db.refresh(inv)
    assert inv.status == "partially_paid"


def test_record_payment_multiple_times_until_full(
    client: TestClient, db: Session
) -> None:
    """Test thanh toán nhiều lần cho đến khi hoàn tất hóa đơn."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db, total_amount=600_000.0)
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    # Lần 1: Thanh toán 200,000 bằng tiền mặt
    res1 = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 200_000.0,
            "payment_method": "cash",
            "note": "Thanh toán đợt 1 tiền mặt",
        },
    )
    assert res1.status_code == 201
    assert res1.json()["data"]["invoice_status_after_payment"] == "partially_paid"

    # Lần 2: Thanh toán phần còn lại 400,000 bằng chuyển khoản với mã giao dịch
    res2 = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 400_000.0,
            "payment_method": "bank_transfer",
            "transaction_code": f"VNPAY-{uuid.uuid4().hex[:6].upper()}",
            "note": "Thanh toán đợt 2 qua QR chuyển khoản",
        },
    )
    assert res2.status_code == 201
    assert res2.json()["data"]["invoice_status_after_payment"] == "paid"
    assert res2.json()["data"]["invoice_remaining_amount"] == 0.0

    db.refresh(inv)
    assert inv.status == "paid"


def test_record_payment_invoice_not_found(client: TestClient, db: Session) -> None:
    """Test thanh toán thất bại khi hóa đơn không tồn tại (404)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    random_id = str(uuid.uuid4())

    response = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": random_id,
            "amount": 300_000.0,
            "payment_method": "cash",
        },
    )
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


def test_record_payment_amount_zero_or_negative(
    client: TestClient, db: Session
) -> None:
    """Test số tiền thanh toán <= 0 bị từ chối (422 validation error)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db)
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    res_zero = client.post(
        "/api/payments",
        headers=headers,
        json={"invoice_id": str(inv.id), "amount": 0.0, "payment_method": "cash"},
    )
    assert res_zero.status_code == 422

    res_neg = client.post(
        "/api/payments",
        headers=headers,
        json={"invoice_id": str(inv.id), "amount": -50_000.0, "payment_method": "cash"},
    )
    assert res_neg.status_code == 422


def test_record_payment_amount_exceeds_remaining(
    client: TestClient, db: Session
) -> None:
    """Test thanh toán số tiền vượt quá số tiền còn nợ bị từ chối (400)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db, total_amount=300_000.0)
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    response = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 400_000.0,
            "payment_method": "cash",
        },
    )
    assert response.status_code == 400
    assert "vượt quá số tiền còn nợ" in response.json()["detail"]


def test_record_payment_duplicate_transaction_code(
    client: TestClient, db: Session
) -> None:
    """Test chặn trùng mã giao dịch (409 Conflict)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db, total_amount=1_000_000.0)
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    fixed_tx_code = f"MOMO-{uuid.uuid4().hex[:8].upper()}"

    res1 = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 300_000.0,
            "payment_method": "e_wallet",
            "transaction_code": fixed_tx_code,
            "note": "Thanh toán ví Momo",
        },
    )
    assert res1.status_code == 201

    # Thử thanh toán lại với cùng mã giao dịch
    res2 = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 200_000.0,
            "payment_method": "e_wallet",
            "transaction_code": fixed_tx_code,
            "note": "Thanh toán trùng mã giao dịch",
        },
    )
    assert res2.status_code == 409
    assert "đã được ghi nhận trước đó" in res2.json()["detail"]


def test_record_payment_rapid_duplicate_rejection(
    client: TestClient, db: Session
) -> None:
    """Test chống gửi trùng lặp giao dịch trong vòng 60 giây (409 Conflict)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db, total_amount=1_000_000.0)
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    # Giao dịch 1
    res1 = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 250_000.0,
            "payment_method": "cash",
            "note": "Khách thanh toán tiền mặt",
        },
    )
    assert res1.status_code == 201

    # Giao dịch 2 (gửi lại ngay lập tức cùng số tiền, phương thức, không có mã GD)
    res2 = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 250_000.0,
            "payment_method": "cash",
            "note": "Gửi trùng lặp",
        },
    )
    assert res2.status_code == 409
    assert "trong vòng 60 giây" in res2.json()["detail"]


def test_record_payment_non_cash_verification_required(
    client: TestClient, db: Session
) -> None:
    """Test phương thức phi tiền mặt yêu cầu mã giao dịch hoặc ghi chú xác minh (400)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db, total_amount=500_000.0)
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    # Không có mã GD và không có note -> 400
    res_fail = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 200_000.0,
            "payment_method": "bank_transfer",
            "transaction_code": None,
            "note": None,
        },
    )
    assert res_fail.status_code == 400
    assert "cần cung cấp mã giao dịch" in res_fail.json()["detail"]

    # Có mã GD -> thành công
    res_ok = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 200_000.0,
            "payment_method": "bank_transfer",
            "transaction_code": f"VCB-{uuid.uuid4().hex[:6].upper()}",
            "note": "Xác nhận đã nhận chuyển khoản",
        },
    )
    assert res_ok.status_code == 201


def test_record_payment_already_paid_invoice(client: TestClient, db: Session) -> None:
    """Test chặn thanh toán hóa đơn đã hoàn tất (400)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db, total_amount=300_000.0, status="paid")
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    response = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 100_000.0,
            "payment_method": "cash",
        },
    )
    assert response.status_code == 400
    assert "đã được thanh toán đầy đủ" in response.json()["detail"]


def test_record_payment_cancelled_invoice(client: TestClient, db: Session) -> None:
    """Test chặn thanh toán hóa đơn đã bị hủy (400)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db, total_amount=300_000.0, status="cancelled")
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    response = client.post(
        "/api/payments",
        headers=headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 100_000.0,
            "payment_method": "cash",
        },
    )
    assert response.status_code == 400
    assert "đã bị hủy" in response.json()["detail"]


def test_record_payment_rbac_permissions(client: TestClient, db: Session) -> None:
    """Test phân quyền truy cập API ghi nhận thanh toán."""
    fix = setup_invoice_fixture(db, total_amount=500_000.0)
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    # 1. Anonymous -> 401
    res_anon = client.post(
        "/api/payments",
        json={"invoice_id": str(inv.id), "amount": 100_000.0, "payment_method": "cash"},
    )
    assert res_anon.status_code == 401

    # 2. Customer -> 403 Forbidden
    cust_user = create_role_user(db, "customer")
    res_cust = client.post(
        "/api/payments",
        headers=get_token_headers(cust_user),
        json={"invoice_id": str(inv.id), "amount": 100_000.0, "payment_method": "cash"},
    )
    assert res_cust.status_code == 403

    # 3. Staff -> 201 Created
    staff_user = create_role_user(db, "staff")
    res_staff = client.post(
        "/api/payments",
        headers=get_token_headers(staff_user),
        json={"invoice_id": str(inv.id), "amount": 100_000.0, "payment_method": "cash"},
    )
    assert res_staff.status_code == 201


def test_get_payment_detail_and_invoice_payments(
    client: TestClient, db: Session
) -> None:
    """Test tra cứu chi tiết giao dịch thanh toán và danh sách theo hóa đơn."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db, total_amount=400_000.0)
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    res_pay = client.post(
        "/api/payments",
        headers=headers,
        json={"invoice_id": str(inv.id), "amount": 400_000.0, "payment_method": "cash"},
    )
    assert res_pay.status_code == 201
    pay_id = res_pay.json()["data"]["id"]

    # Tra cứu theo payment_id
    res_detail = client.get(f"/api/payments/{pay_id}", headers=headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["data"]["id"] == pay_id

    # Tra cứu danh sách theo invoice_id
    res_by_inv = client.get(f"/api/payments/by-invoice/{inv.id}", headers=headers)
    assert res_by_inv.status_code == 200
    assert res_by_inv.json()["count"] >= 1


def test_record_payment_database_rollback_on_error(
    client: TestClient, db: Session
) -> None:
    """Test rollback cơ sở dữ liệu khi phát sinh lỗi trong quá trình ghi nhận thanh toán."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_invoice_fixture(db, total_amount=500_000.0)
    inv = fix["invoice"]
    assert isinstance(inv, Invoice)

    with patch.object(
        Session, "commit", side_effect=RuntimeError("Lỗi kết nối cơ sở dữ liệu giả lập")
    ):
        response = client.post(
            "/api/payments",
            headers=headers,
            json={
                "invoice_id": str(inv.id),
                "amount": 200_000.0,
                "payment_method": "cash",
            },
        )
        assert response.status_code == 500

    # Đảm bảo không có thanh toán nào được lưu và trạng thái hóa đơn không đổi
    payments = db.exec(select(Payment).where(Payment.invoice_id == inv.id)).all()
    assert len(payments) == 0
    db.refresh(inv)
    assert inv.status == "unpaid"
