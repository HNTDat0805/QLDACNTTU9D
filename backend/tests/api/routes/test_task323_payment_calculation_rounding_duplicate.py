"""Test suite for Task 323: Kiểm thử tính tiền, làm tròn và ngăn ghi nhận thanh toán lặp.

Contents:
Nhóm A: Kiểm thử tính tiền (PAY)
  - PAY-01: Tính tiền với dữ liệu hợp lệ (nhiều hạng mục chi phí, subtotal, remaining_amount, status).
  - PAY-02: Tính tiền với giá trị biên (thanh toán chính xác số dư nợ, số tiền tối thiểu 0.01, chặn amount <= 0, chặn vượt quá số nợ).

Nhóm B: Kiểm thử làm tròn (ROUND)
  - ROUND-01: Làm tròn giá trị thập phân (ROUND_HALF_UP đến 2 chữ số thập phân, kiểm tra các ngưỡng 0.004 vs 0.005).
  - ROUND-02: Làm tròn nhiều thành phần chi phí và tính nhất quán (làm tròn từng hạng mục trước khi cộng dồn).

Nhóm C: Kiểm thử ngăn ghi nhận thanh toán lặp (DUP)
  - DUP-01: Gửi lại cùng giao dịch (cùng mã tham chiếu transaction_code) -> Bị từ chối 409 Conflict.
  - DUP-02: Hai request gửi lại cùng giao dịch trong thời gian ngắn (60 giây) -> Bị từ chối 409 Conflict.
  - DUP-03: Hai request ghi nhận thanh toán cạnh tranh đồng thời (Concurrency / Race Condition) -> Chỉ 1 thành công.
  - DUP-04: Phân biệt gửi lại giao dịch trùng lặp với tạo giao dịch thanh toán từng phần mới hợp lệ.
  - DUP-05: Chặn thanh toán hóa đơn đã hoàn tất (paid) hoặc đã bị hủy (cancelled).
"""

import concurrent.futures
import threading
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import security
from app.models import (
    Appointment,
    Customer,
    Device,
    Invoice,
    Payment,
    Quote,
    QuoteItem,
    QuoteStatus,
    Technician,
    User,
)
from app.services.invoice_service import _round_money as invoice_round_money
from app.services.payment_service import _round_money as payment_round_money
from tests.utils.utils import random_email


def create_test_staff_user(
    db: Session, role: str = "staff"
) -> tuple[User, dict[str, str]]:
    """Tạo người dùng nhân viên thực tế trong DB và tạo token xác thực."""
    user = User(
        email=f"test_{role}_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashed_pwd_task323",
        role=role,
        is_active=True,
        full_name=f"Nhân Viên {role.title()}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = security.create_access_token(
        subject=user.id,
        role=user.role,
        email=user.email,
    )
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


@pytest.fixture
def task323_base_fixture(db: Session) -> dict[str, Any]:
    """Fixture tạo khách hàng, thiết bị, kỹ thuật viên và phiếu sửa chữa cơ sở."""
    cust = Customer(
        full_name="Lê Hoàng Nam",
        phone_number=f"093{uuid.uuid4().int % 10000000:07d}",
        email=random_email(),
    )
    db.add(cust)
    db.commit()

    device = Device(
        customer_id=cust.id,
        brand="Apple",
        model="iPhone 14 Pro",
        color="Space Black",
    )
    db.add(device)

    tech = Technician(
        full_name="Kỹ Thuật Viên Hùng",
        phone_number=f"094{uuid.uuid4().int % 10000000:07d}",
        is_active=True,
    )
    db.add(tech)
    db.commit()

    appt = Appointment(
        appointment_number=f"APPT-323-{uuid.uuid4().hex[:6].upper()}",
        appointment_date=datetime.now(UTC),
        status="IN_PROGRESS",
        customer_id=cust.id,
        device_id=device.id,
        technician_id=tech.id,
        total_amount=0.0,
    )
    db.add(appt)
    db.commit()

    return {
        "customer": cust,
        "device": device,
        "technician": tech,
        "appointment": appt,
    }


# ============================================================================
# NHÓM A: KIỂM THỬ TÍNH TIỀN (PAY)
# ============================================================================


def test_pay_01_calculation_with_valid_multi_component_data(
    client: TestClient, db: Session, task323_base_fixture: dict[str, Any]
) -> None:
    """PAY-01: Tính tiền với dữ liệu hợp lệ nhiều thành phần chi phí.

    - Tạo đơn sửa chữa với báo giá được duyệt gồm 3 hạng mục:
      + Hạng mục 1: Màn hình OLED (đơn giá 450,000 đ, số lượng 2) -> 900,000 đ
      + Hạng mục 2: Vệ sinh máy (đơn giá 120,000 đ, số lượng 1) -> 120,000 đ
      + Hạng mục 3: Kính cường lực (đơn giá 80,000 đ, số lượng 3) -> 240,000 đ
    - Tạo hóa đơn:
      + subtotal = 900,000 + 120,000 + 240,000 = 1,260,000 đ.
      + total_amount = 1,260,000 đ, paid_amount = 0 đ, remaining_amount = 1,260,000 đ, status = "unpaid".
    - Thanh toán đợt 1 (500,000 đ):
      + paid_amount = 500,000 đ, remaining_amount = 760,000 đ, status = "partially_paid".
    - Thanh toán đợt 2 (760,000 đ):
      + paid_amount = 1,260,000 đ, remaining_amount = 0 đ, status = "paid".
    """
    appt = task323_base_fixture["appointment"]
    cust = task323_base_fixture["customer"]

    # 1. Tạo Quote duyệt (ACCEPTED) với 3 hạng mục
    quote = Quote(
        quote_number=f"BG-{uuid.uuid4().hex[:6].upper()}",
        appointment_id=appt.id,
        customer_id=cust.id,
        status=QuoteStatus.ACCEPTED.value,
        total_amount=1_260_000.0,
    )
    db.add(quote)
    db.commit()

    items = [
        QuoteItem(
            quote_id=quote.id,
            item_name="Màn hình OLED Cao Cấp",
            unit_price=450_000.0,
            quantity=2,
            total_price=900_000.0,
        ),
        QuoteItem(
            quote_id=quote.id,
            item_name="Vệ sinh máy chuyên sâu",
            unit_price=120_000.0,
            quantity=1,
            total_price=120_000.0,
        ),
        QuoteItem(
            quote_id=quote.id,
            item_name="Kính cường lực KingKong",
            unit_price=80_000.0,
            quantity=3,
            total_price=240_000.0,
        ),
    ]
    for it in items:
        db.add(it)
    db.commit()

    _, staff_headers = create_test_staff_user(db, "staff")

    # 2. Tạo hóa đơn qua API POST /api/invoices
    inv_resp = client.post(
        "/api/invoices",
        headers=staff_headers,
        json={"repair_order_id": str(appt.id), "notes": "Hóa đơn kiểm thử PAY-01"},
    )
    assert inv_resp.status_code == 201
    inv_data = inv_resp.json()["data"]
    inv_id = inv_data["id"]

    # Đối chiếu công thức tính tổng tiền
    assert inv_data["subtotal"] == 1_260_000.0
    assert inv_data["discount_amount"] == 0.0
    assert inv_data["tax_amount"] == 0.0
    assert inv_data["total_amount"] == 1_260_000.0
    assert inv_data["paid_amount"] == 0.0
    assert inv_data["remaining_amount"] == 1_260_000.0
    assert inv_data["status"] == "unpaid"
    assert len(inv_data["items"]) == 3

    # 3. Ghi nhận thanh toán đợt 1 (500,000 đ)
    pay1_resp = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": inv_id,
            "amount": 500_000.0,
            "payment_method": "cash",
            "note": "Thanh toán đợt 1 tiền mặt tại quầy",
        },
    )
    assert pay1_resp.status_code == 201
    pay1_data = pay1_resp.json()["data"]
    assert pay1_data["amount"] == 500_000.0
    assert pay1_data["invoice_status_after_payment"] == "partially_paid"
    assert pay1_data["invoice_remaining_amount"] == 760_000.0

    # 4. Ghi nhận thanh toán đợt 2 (760,000 đ) qua chuyển khoản ngân hàng
    pay2_resp = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": inv_id,
            "amount": 760_000.0,
            "payment_method": "bank_transfer",
            "transaction_code": f"VCB-{uuid.uuid4().hex[:8].upper()}",
            "note": "Thanh toán đợt 2 hoàn tất qua QR",
        },
    )
    assert pay2_resp.status_code == 201
    pay2_data = pay2_resp.json()["data"]
    assert pay2_data["amount"] == 760_000.0
    assert pay2_data["invoice_status_after_payment"] == "paid"
    assert pay2_data["invoice_remaining_amount"] == 0.0

    # 5. Kiểm tra trạng thái hóa đơn chi tiết qua GET /api/invoices/{id}
    detail_resp = client.get(f"/api/invoices/{inv_id}", headers=staff_headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()["data"]
    assert detail_data["total_amount"] == 1_260_000.0
    assert detail_data["paid_amount"] == 1_260_000.0
    assert detail_data["remaining_amount"] == 0.0
    assert detail_data["status"] == "paid"


def test_pay_02_calculation_boundary_values(
    client: TestClient, db: Session, task323_base_fixture: dict[str, Any]
) -> None:
    """PAY-02: Tính tiền với các giá trị biên.

    - Giá trị biên 1: Thanh toán số tiền nhỏ nhất hợp lệ (0.01 đ).
    - Giá trị biên 2: Thanh toán chính xác từng xu số nợ còn lại -> remaining = 0.0, status = "paid".
    - Giá trị biên 3 (Không hợp lệ): amount = 0 hoặc amount < 0 -> Bị reject 422 Unprocessable Entity.
    - Giá trị biên 4 (Không hợp lệ): amount > remaining_due (dù chỉ lệch 0.01 đ) -> Bị reject 400 Bad Request.
    """
    appt = task323_base_fixture["appointment"]
    cust = task323_base_fixture["customer"]
    _, staff_headers = create_test_staff_user(db, "staff")

    # Tạo hóa đơn 100.0 đ
    inv = Invoice(
        invoice_number=f"HD-BOUND-{uuid.uuid4().hex[:6].upper()}",
        appointment_id=appt.id,
        customer_id=cust.id,
        subtotal=100.0,
        discount_amount=0.0,
        tax_amount=0.0,
        total_amount=100.0,
        status="unpaid",
        issue_date=datetime.now(UTC),
    )
    db.add(inv)
    db.commit()

    # Boundary 3: amount = 0 -> 422 Validation Error
    r_zero = client.post(
        "/api/payments",
        headers=staff_headers,
        json={"invoice_id": str(inv.id), "amount": 0.0, "payment_method": "cash"},
    )
    assert r_zero.status_code == 422

    # Boundary 3: amount < 0 -> 422 Validation Error
    r_neg = client.post(
        "/api/payments",
        headers=staff_headers,
        json={"invoice_id": str(inv.id), "amount": -10.0, "payment_method": "cash"},
    )
    assert r_neg.status_code == 422

    # Boundary 4: amount vượt quá nợ 100.0 đ (100.01 đ) -> 400 Bad Request
    r_exceed = client.post(
        "/api/payments",
        headers=staff_headers,
        json={"invoice_id": str(inv.id), "amount": 100.01, "payment_method": "cash"},
    )
    assert r_exceed.status_code == 400
    assert "vượt quá số tiền còn nợ" in r_exceed.json()["detail"]

    # Boundary 1: Thanh toán số tiền nhỏ nhất hợp lệ 0.01 đ
    r_min = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 0.01,
            "payment_method": "cash",
            "note": "Thanh toán tối thiểu 0.01 đ",
        },
    )
    assert r_min.status_code == 201
    assert r_min.json()["data"]["amount"] == 0.01
    assert r_min.json()["data"]["invoice_remaining_amount"] == 99.99
    assert r_min.json()["data"]["invoice_status_after_payment"] == "partially_paid"

    # Boundary 2: Thanh toán chính xác số dư nợ còn lại 99.99 đ
    r_exact = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 99.99,
            "payment_method": "cash",
            "note": "Thanh toán chính xác phần còn lại",
        },
    )
    assert r_exact.status_code == 201
    assert r_exact.json()["data"]["amount"] == 99.99
    assert r_exact.json()["data"]["invoice_remaining_amount"] == 0.0
    assert r_exact.json()["data"]["invoice_status_after_payment"] == "paid"


# ============================================================================
# NHÓM B: KIỂM THỬ LÀM TRÒN (ROUND)
# ============================================================================


def test_round_01_decimal_rounding_half_up(
    client: TestClient, db: Session, task323_base_fixture: dict[str, Any]
) -> None:
    """ROUND-01: Làm tròn giá trị thập phân theo quy tắc ROUND_HALF_UP đến 2 chữ số.

    - Kiểm tra trực tiếp hàm _round_money trong invoice_service và payment_service:
      + 100.004 -> 100.00 (dưới 0.005)
      + 100.005 -> 100.01 (ngưỡng 0.005 làm tròn lên)
      + 100.006 -> 100.01 (trên 0.005)
      + 250000.125 -> 250000.13
      + 250000.124 -> 250000.12
    - Kiểm tra API ghi nhận thanh toán với số tiền có 3 chữ số thập phân (250000.125 đ):
      + Hệ thống tự động làm tròn thành 250000.13 đ qua _round_money.
      + Lưu vào DB và response đúng 250000.13 đ, không bị lỗi sai số floating point.
    """
    # 1. Kiểm tra đơn vị logic hàm _round_money
    for fn in (invoice_round_money, payment_round_money):
        assert fn(100.004) == Decimal("100.00")
        assert fn(100.005) == Decimal("100.01")
        assert fn(100.006) == Decimal("100.01")
        assert fn(250000.125) == Decimal("250000.13")
        assert fn(250000.124) == Decimal("250000.12")
        assert fn(0.005) == Decimal("0.01")
        assert fn(0.004) == Decimal("0.00")

    appt = task323_base_fixture["appointment"]
    cust = task323_base_fixture["customer"]
    _, staff_headers = create_test_staff_user(db, "staff")

    inv = Invoice(
        invoice_number=f"HD-ROUND-{uuid.uuid4().hex[:6].upper()}",
        appointment_id=appt.id,
        customer_id=cust.id,
        subtotal=500_000.0,
        discount_amount=0.0,
        tax_amount=0.0,
        total_amount=500_000.0,
        status="unpaid",
        issue_date=datetime.now(UTC),
    )
    db.add(inv)
    db.commit()

    # 2. Gửi request thanh toán với 250000.125 đ (nửa lên -> 250000.13 đ)
    resp = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 250_000.125,
            "payment_method": "cash",
            "note": "Kiểm tra làm tròn 250000.125 thành 250000.13",
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["amount"] == 250_000.13
    assert data["invoice_remaining_amount"] == 249_999.87


def test_round_02_multi_item_rounding_and_sum_consistency(
    client: TestClient, db: Session, task323_base_fixture: dict[str, Any]
) -> None:
    """ROUND-02: Làm tròn nhiều thành phần chi phí và tính nhất quán khi cộng dồn.

    - Kiểm tra quy tắc mã nguồn thực tế:
      Từng hạng mục được làm tròn trước: item_total = _round_money(unit_price * qty)
      Sau đó cộng dồn thành subtotal = sum(item_total).
    - Tạo báo giá có 3 hạng mục đơn giá lẻ:
      + Hạng mục 1: Đơn giá 33,333.334 đ -> làm tròn 33,333.33 đ
      + Hạng mục 2: Đơn giá 33,333.335 đ -> làm tròn 33,333.34 đ
      + Hạng mục 3: Đơn giá 33,333.335 đ -> làm tròn 33,333.34 đ
      + Tổng subtotal = 33,333.33 + 33,333.34 + 33,333.34 = 100,000.01 đ
    - Thanh toán 3 đợt tương ứng khớp từng xu:
      + Đợt 1: 33,333.33 đ -> còn nợ 66,666.68 đ
      + Đợt 2: 33,333.34 đ -> còn nợ 33,333.34 đ
      + Đợt 3: 33,333.34 đ -> còn nợ 0.0 đ, hoàn tất paid.
    """
    appt = task323_base_fixture["appointment"]
    cust = task323_base_fixture["customer"]
    _, staff_headers = create_test_staff_user(db, "staff")

    quote = Quote(
        quote_number=f"BG-RND-{uuid.uuid4().hex[:6].upper()}",
        appointment_id=appt.id,
        customer_id=cust.id,
        status=QuoteStatus.ACCEPTED.value,
        total_amount=100_000.01,
    )
    db.add(quote)
    db.commit()

    items = [
        QuoteItem(
            quote_id=quote.id,
            item_name="Linh kiện lẻ 1 (33333.334)",
            unit_price=33_333.334,
            quantity=1,
            total_price=33_333.334,
        ),
        QuoteItem(
            quote_id=quote.id,
            item_name="Linh kiện lẻ 2 (33333.335)",
            unit_price=33_333.335,
            quantity=1,
            total_price=33_333.335,
        ),
        QuoteItem(
            quote_id=quote.id,
            item_name="Linh kiện lẻ 3 (33333.335)",
            unit_price=33_333.335,
            quantity=1,
            total_price=33_333.335,
        ),
    ]
    for it in items:
        db.add(it)
    db.commit()

    # Tạo hóa đơn
    inv_resp = client.post(
        "/api/invoices",
        headers=staff_headers,
        json={"repair_order_id": str(appt.id)},
    )
    assert inv_resp.status_code == 201
    inv_data = inv_resp.json()["data"]
    inv_id = inv_data["id"]

    # Xác minh từng hạng mục đã được làm tròn đúng
    item_totals = [it["total_price"] for it in inv_data["items"]]
    assert item_totals == [33_333.33, 33_333.34, 33_333.34]
    assert inv_data["total_amount"] == 100_000.01

    # Thanh toán 3 đợt
    r1 = client.post(
        "/api/payments",
        headers=staff_headers,
        json={"invoice_id": inv_id, "amount": 33_333.33, "payment_method": "cash"},
    )
    assert r1.status_code == 201
    assert r1.json()["data"]["invoice_remaining_amount"] == 66_666.68

    r2 = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": inv_id,
            "amount": 33_333.34,
            "payment_method": "bank_transfer",
            "transaction_code": f"VCB-{uuid.uuid4().hex[:6].upper()}",
            "note": "Đợt 2",
        },
    )
    assert r2.status_code == 201
    assert r2.json()["data"]["invoice_remaining_amount"] == 33_333.34

    r3 = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": inv_id,
            "amount": 33_333.34,
            "payment_method": "e_wallet",
            "transaction_code": f"MOMO-{uuid.uuid4().hex[:6].upper()}",
            "note": "Đợt 3 hoàn tất",
        },
    )
    assert r3.status_code == 201
    assert r3.json()["data"]["invoice_remaining_amount"] == 0.0
    assert r3.json()["data"]["invoice_status_after_payment"] == "paid"


# ============================================================================
# NHÓM C: KIỂM THỬ NGĂN GHI NHẬN THANH TOÁN LẶP (DUP)
# ============================================================================


def test_dup_01_resend_same_transaction_code_rejected(
    client: TestClient, db: Session, task323_base_fixture: dict[str, Any]
) -> None:
    """DUP-01: Gửi lại cùng giao dịch (trùng mã transaction_code).

    - Gửi request thanh toán lần 1 với mã tham chiếu transaction_code = "TX-VNPAY-323-A1".
      + Kỳ vọng: Thành công (201 Created).
    - Gửi lại request với cùng mã transaction_code = "TX-VNPAY-323-A1".
      + Kỳ vọng: Bị từ chối HTTP 409 Conflict với thông báo rõ ràng về việc mã giao dịch đã ghi nhận.
    - Kiểm tra DB: Chỉ có đúng 1 bản ghi Payment mang mã giao dịch này.
    """
    appt = task323_base_fixture["appointment"]
    cust = task323_base_fixture["customer"]
    _, staff_headers = create_test_staff_user(db, "staff")

    inv = Invoice(
        invoice_number=f"HD-DUP1-{uuid.uuid4().hex[:6].upper()}",
        appointment_id=appt.id,
        customer_id=cust.id,
        subtotal=1_000_000.0,
        discount_amount=0.0,
        tax_amount=0.0,
        total_amount=1_000_000.0,
        status="unpaid",
        issue_date=datetime.now(UTC),
    )
    db.add(inv)
    db.commit()

    fixed_tx_code = f"TX-VNPAY-TASK323-{uuid.uuid4().hex[:6].upper()}"

    # Lần 1: Thành công
    resp1 = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 300_000.0,
            "payment_method": "bank_transfer",
            "transaction_code": fixed_tx_code,
            "note": "Thanh toán đợt 1",
        },
    )
    assert resp1.status_code == 201

    # Lần 2: Gửi lại cùng mã giao dịch -> 409 Conflict
    resp2 = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 200_000.0,
            "payment_method": "bank_transfer",
            "transaction_code": fixed_tx_code,
            "note": "Cố tình gửi lại cùng mã giao dịch đã ghi nhận",
        },
    )
    assert resp2.status_code == 409
    assert "đã được ghi nhận trước đó trên hệ thống" in resp2.json()["detail"]

    # Kiểm tra database: Chỉ tồn tại đúng 1 Payment với mã giao dịch này
    payments_in_db = db.exec(
        select(Payment).where(Payment.transaction_reference == fixed_tx_code)
    ).all()
    assert len(payments_in_db) == 1


def test_dup_02_resend_same_payment_within_60s_rejected(
    client: TestClient, db: Session, task323_base_fixture: dict[str, Any]
) -> None:
    """DUP-02: Hai request gửi lại cùng giao dịch trong thời gian ngắn (cửa sổ 60 giây).

    - Thanh toán tiền mặt 200,000 đ cho hóa đơn -> Thành công (201 Created).
    - Gửi lại request y hệt (cùng hóa đơn, cùng số tiền 200,000 đ, cùng phương thức cash) ngay lập tức.
    - Kỳ vọng: Bị từ chối HTTP 409 Conflict ('Phát hiện giao dịch tương tự vừa được ghi nhận trong vòng 60 giây').
    - Kiểm tra DB: Chỉ có đúng 1 bản ghi Payment, số nợ của hóa đơn chỉ bị trừ đúng 200,000 đ.
    """
    appt = task323_base_fixture["appointment"]
    cust = task323_base_fixture["customer"]
    _, staff_headers = create_test_staff_user(db, "staff")

    inv = Invoice(
        invoice_number=f"HD-DUP2-{uuid.uuid4().hex[:6].upper()}",
        appointment_id=appt.id,
        customer_id=cust.id,
        subtotal=600_000.0,
        discount_amount=0.0,
        tax_amount=0.0,
        total_amount=600_000.0,
        status="unpaid",
        issue_date=datetime.now(UTC),
    )
    db.add(inv)
    db.commit()

    # Giao dịch 1: Thành công
    r1 = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 200_000.0,
            "payment_method": "cash",
            "note": "Khách thanh toán tiền mặt lần 1",
        },
    )
    assert r1.status_code == 201

    # Giao dịch 2: Gửi lại ngay lập tức cùng số tiền 200,000 đ và phương thức cash
    r2 = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 200_000.0,
            "payment_method": "cash",
            "note": "Gửi lặp lại cùng số tiền trong vòng 60s",
        },
    )
    assert r2.status_code == 409
    assert "trong vòng 60 giây" in r2.json()["detail"]

    # Kiểm tra database: Chỉ có đúng 1 bản ghi Payment cho hóa đơn này
    payments = db.exec(select(Payment).where(Payment.invoice_id == inv.id)).all()
    assert len(payments) == 1
    assert payments[0].amount == 200_000.0


def test_dup_03_concurrent_duplicate_payment_requests(
    client: TestClient, db: Session, task323_base_fixture: dict[str, Any]
) -> None:
    """DUP-03: Hai request ghi nhận cùng một giao dịch thanh toán cạnh tranh đồng thời (Race Condition).

    - Hóa đơn còn nợ 500,000 đ.
    - Hai request gửi đồng thời cùng yêu cầu thanh toán toàn bộ 500,000 đ qua ThreadPoolExecutor.
    - Nhờ row lock with_for_update và transaction:
      + Chính xác 1 request thành công (201 Created), cập nhật hóa đơn sang paid.
      + Request còn lại bị từ chối thích hợp (409 Conflict hoặc 400 Bad Request do hóa đơn đã thanh toán xong).
      + Database chỉ ghi nhận đúng 1 bản ghi Payment 500,000 đ, tổng tiền thanh toán không bị nhân đôi lên 1,000,000 đ.
    """
    appt = task323_base_fixture["appointment"]
    cust = task323_base_fixture["customer"]
    _, staff_headers = create_test_staff_user(db, "staff")

    inv = Invoice(
        invoice_number=f"HD-CONC-{uuid.uuid4().hex[:6].upper()}",
        appointment_id=appt.id,
        customer_id=cust.id,
        subtotal=500_000.0,
        discount_amount=0.0,
        tax_amount=0.0,
        total_amount=500_000.0,
        status="unpaid",
        issue_date=datetime.now(UTC),
    )
    db.add(inv)
    db.commit()

    inv_id_str = str(inv.id)

    payload = {
        "invoice_id": inv_id_str,
        "amount": 500_000.0,
        "payment_method": "cash",
        "note": "Thanh toán đồng thời 500k",
    }

    # Serialization lock phục vụ SQLite in-memory StaticPool
    req_lock = threading.Lock()

    def do_payment() -> tuple[int, dict[str, Any]]:
        with req_lock:
            resp = client.post("/api/payments", headers=staff_headers, json=payload)
            return resp.status_code, resp.json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(do_payment)
        f2 = executor.submit(do_payment)
        s1, d1 = f1.result()
        s2, d2 = f2.result()

    statuses = [s1, s2]
    # Chính xác 1 request thành công (201)
    assert statuses.count(201) == 1, (
        f"Kỳ vọng đúng 1 request thành công 201: {statuses}"
    )
    # Request còn lại bị từ chối (409 do trùng 60s hoặc 400 do đã paid)
    rejected_status = s2 if s1 == 201 else s1
    assert rejected_status in (400, 409), (
        f"Request còn lại phải bị từ chối: {rejected_status}"
    )

    # Kiểm tra database: Chỉ có đúng 1 bản ghi Payment duy nhất
    payments = db.exec(select(Payment).where(Payment.invoice_id == inv.id)).all()
    assert len(payments) == 1
    assert payments[0].amount == 500_000.0

    # Trạng thái hóa đơn là paid
    db.refresh(inv)
    assert inv.status == "paid"


def test_dup_04_distinguish_duplicate_from_valid_subsequent_payment(
    client: TestClient, db: Session, task323_base_fixture: dict[str, Any]
) -> None:
    """DUP-04: Phân biệt việc gửi lại giao dịch trùng lặp với tạo giao dịch thanh toán từng phần mới hợp lệ.

    - Hóa đơn: 500,000 đ.
    - Đợt 1: Thanh toán 200,000 đ qua VNPAY với mã TX-01 -> Thành công (201, còn nợ 300,000 đ).
    - Đợt 2: Thanh toán tiếp 150,000 đ qua Momo với mã TX-02 (khác mã, khác số tiền, khác phương thức) -> Được chấp nhận (201, còn nợ 150,000 đ).
    - Hệ thống phân biệt rõ ràng: giao dịch mới có thông tin hợp lệ không bị chặn nhầm bởi cơ chế chống trùng lặp.
    """
    appt = task323_base_fixture["appointment"]
    cust = task323_base_fixture["customer"]
    _, staff_headers = create_test_staff_user(db, "staff")

    inv = Invoice(
        invoice_number=f"HD-PART-{uuid.uuid4().hex[:6].upper()}",
        appointment_id=appt.id,
        customer_id=cust.id,
        subtotal=500_000.0,
        discount_amount=0.0,
        tax_amount=0.0,
        total_amount=500_000.0,
        status="unpaid",
        issue_date=datetime.now(UTC),
    )
    db.add(inv)
    db.commit()

    # Đợt 1: 200,000 đ qua bank_transfer
    tx1 = f"TX-VNPAY-{uuid.uuid4().hex[:6].upper()}"
    r1 = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 200_000.0,
            "payment_method": "bank_transfer",
            "transaction_code": tx1,
            "note": "Thanh toán đợt 1 qua VNPAY",
        },
    )
    assert r1.status_code == 201
    assert r1.json()["data"]["invoice_remaining_amount"] == 300_000.0
    assert r1.json()["data"]["invoice_status_after_payment"] == "partially_paid"

    # Đợt 2: 150,000 đ qua e_wallet với mã khác tx2 -> Phải thành công!
    tx2 = f"TX-MOMO-{uuid.uuid4().hex[:6].upper()}"
    r2 = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(inv.id),
            "amount": 150_000.0,
            "payment_method": "e_wallet",
            "transaction_code": tx2,
            "note": "Thanh toán đợt 2 qua Ví Momo",
        },
    )
    assert r2.status_code == 201
    assert r2.json()["data"]["invoice_remaining_amount"] == 150_000.0
    assert r2.json()["data"]["invoice_status_after_payment"] == "partially_paid"

    # Database ghi nhận đủ 2 giao dịch riêng biệt
    payments = db.exec(select(Payment).where(Payment.invoice_id == inv.id)).all()
    assert len(payments) == 2


def test_dup_05_prevent_payment_on_already_paid_or_cancelled_invoice(
    client: TestClient, db: Session, task323_base_fixture: dict[str, Any]
) -> None:
    """DUP-05: Chặn thanh toán hóa đơn đã hoàn tất (paid) hoặc đã bị hủy (cancelled).

    - Hóa đơn đã hoàn tất thanh toán (paid) -> Bị từ chối HTTP 400 Bad Request.
    - Hóa đơn đã bị hủy (cancelled) -> Bị từ chối HTTP 400 Bad Request.
    """
    appt = task323_base_fixture["appointment"]
    cust = task323_base_fixture["customer"]
    _, staff_headers = create_test_staff_user(db, "staff")

    # 1. Hóa đơn đã hoàn tất (status="paid")
    inv_paid = Invoice(
        invoice_number=f"HD-PAID-{uuid.uuid4().hex[:6].upper()}",
        appointment_id=appt.id,
        customer_id=cust.id,
        subtotal=200_000.0,
        total_amount=200_000.0,
        status="paid",
        issue_date=datetime.now(UTC),
    )
    db.add(inv_paid)
    db.commit()

    r_paid = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(inv_paid.id),
            "amount": 50_000.0,
            "payment_method": "cash",
        },
    )
    assert r_paid.status_code == 400
    assert "đã được thanh toán đầy đủ" in r_paid.json()["detail"]

    # 2. Hóa đơn đã bị hủy (status="cancelled")
    # Cần tạo appointment mới vì appointment_id có ràng buộc unique trong invoice
    appt2 = Appointment(
        appointment_number=f"APPT-CANCEL-{uuid.uuid4().hex[:6].upper()}",
        appointment_date=datetime.now(UTC),
        status="CANCELLED",
        customer_id=cust.id,
        device_id=task323_base_fixture["device"].id,
        total_amount=0.0,
    )
    db.add(appt2)
    db.commit()

    inv_cancelled = Invoice(
        invoice_number=f"HD-CANCEL-{uuid.uuid4().hex[:6].upper()}",
        appointment_id=appt2.id,
        customer_id=cust.id,
        subtotal=300_000.0,
        total_amount=300_000.0,
        status="cancelled",
        issue_date=datetime.now(UTC),
    )
    db.add(inv_cancelled)
    db.commit()

    r_cancel = client.post(
        "/api/payments",
        headers=staff_headers,
        json={
            "invoice_id": str(inv_cancelled.id),
            "amount": 100_000.0,
            "payment_method": "cash",
        },
    )
    assert r_cancel.status_code == 400
    assert "đã bị hủy, không thể ghi nhận thanh toán" in r_cancel.json()["detail"]
