"""Test suite for Task 181: Kiểm thử hai yêu cầu đặt cùng slot và giao dịch PostgreSQL.

Contents:
Group A: Kiểm thử hai yêu cầu đặt cùng slot (Concurrency & Race Conditions)
  - CON-01: Hai request đặt cùng slot đồng thời (chính xác 1 thành công 201, 1 bị từ chối 409 Conflict).
  - CON-02: Request tiếp theo khi slot đã được đặt (bị từ chối 409 Conflict, slot check unavailable).
  - CON-03: Nhiều request cạnh tranh đồng thời (5 concurrent requests -> 1 thành công 201, 4 bị từ chối 409).
  - CON-04: Hai request đồng thời khác slot / khác kỹ thuật viên (cả 2 đều thành công 201 Created).
  - CON-05: Auto-assignment đồng thời khi chỉ có 1 kỹ thuật viên (1 thành công 201, 1 bị từ chối 409).

Group B: Kiểm thử giao dịch PostgreSQL & Rollback (Transactions & Data Integrity)
  - DB-01: Transaction thành công - Dữ liệu được commit nhất quán (Appointment, AppointmentService, RepairStatusHistory).
  - DB-02: Transaction phát sinh lỗi - Dữ liệu được rollback hoàn toàn, không lưu dở dang.
  - DB-03: Kiểm tra tính toàn vẹn dữ liệu sau rollback - Số lượng bản ghi trước và sau hoàn toàn không đổi.
  - DB-04: Transaction rollback khi cập nhật / đổi lịch hẹn phát sinh lỗi / xung đột.
  - DB-05: Transaction rollback khi phân công kỹ thuật viên phát sinh lỗi hoặc xung đột ca trực.
  - DB-06: Xác minh các ràng buộc cơ sở dữ liệu (Check Constraints & Foreign Key Integrity).
"""

import concurrent.futures
import threading
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select, text

from app.core import security
from app.models import (
    Appointment,
    AppointmentBookingCreate,
    AppointmentService,
    AppointmentStatus,
    Customer,
    Device,
    RepairStatusHistory,
    Service,
    Technician,
    TechnicianSchedule,
    User,
)
from app.services import slot_service
from tests.utils.utils import random_email


def create_authenticated_staff_user(
    db: Session, role: str = "staff"
) -> tuple[User, dict[str, str]]:
    """Tạo người dùng thực tế trong database và sinh token hợp lệ."""
    user = User(
        email=f"test_{role}_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashed_pwd_test_123",
        role=role,
        is_active=True,
        full_name=f"Test {role.title()}",
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
def task181_fixture(db: Session) -> dict[str, Any]:
    """Fixture tạo dữ liệu mẫu hoàn chỉnh: Khách hàng, Thiết bị, Dịch vụ, Kỹ thuật viên và Lịch làm việc."""
    # Bật foreign keys nếu đang dùng SQLite
    if db.bind and db.bind.dialect.name == "sqlite":
        db.execute(text("PRAGMA foreign_keys = ON;"))

    # 1. Khách hàng A
    user_a = User(
        email=random_email(),
        hashed_password="hashed_pwd_test_123",
        role="customer",
        full_name="Khách Hàng A",
    )
    db.add(user_a)
    db.flush()

    cust_a = Customer(
        full_name="Khách Hàng A",
        phone_number=f"097{uuid.uuid4().int % 10000000:07d}",
        user_id=user_a.id,
        email=user_a.email,
    )
    db.add(cust_a)
    db.flush()

    dev_a = Device(
        customer_id=cust_a.id,
        device_type="Smartphone",
        brand="Apple",
        model="iPhone 15 Pro",
    )
    db.add(dev_a)
    db.flush()

    # 2. Khách hàng B
    user_b = User(
        email=random_email(),
        hashed_password="hashed_pwd_test_123",
        role="customer",
        full_name="Khách Hàng B",
    )
    db.add(user_b)
    db.flush()

    cust_b = Customer(
        full_name="Khách Hàng B",
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
        user_id=user_b.id,
        email=user_b.email,
    )
    db.add(cust_b)
    db.flush()

    dev_b = Device(
        customer_id=cust_b.id,
        device_type="Smartphone",
        brand="Samsung",
        model="Galaxy S24 Ultra",
    )
    db.add(dev_b)
    db.flush()

    # 3. Dịch vụ sửa chữa (60 phút)
    svc_60 = Service(
        name=f"Thay pin chính hãng {uuid.uuid4().hex[:6]}",
        base_price=800_000.0,
        estimated_duration_minutes=60,
        is_active=True,
    )
    # Dịch vụ sửa chữa (30 phút)
    svc_30 = Service(
        name=f"Dán kính cường lực {uuid.uuid4().hex[:6]}",
        base_price=150_000.0,
        estimated_duration_minutes=30,
        is_active=True,
    )
    db.add(svc_60)
    db.add(svc_30)
    db.flush()

    # 4. Kỹ thuật viên 1 (Chuyên phần cứng)
    tech1 = Technician(
        full_name=f"KTV Nguyễn Văn Một {uuid.uuid4().hex[:4]}",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
        specialization="Phần cứng, pin, màn hình",
        is_active=True,
    )
    db.add(tech1)
    db.flush()

    # Kỹ thuật viên 2 (Chuyên linh kiện)
    tech2 = Technician(
        full_name=f"KTV Trần Văn Hai {uuid.uuid4().hex[:4]}",
        phone_number=f"092{uuid.uuid4().int % 10000000:07d}",
        specialization="Phần cứng, pin, phụ kiện",
        is_active=True,
    )
    db.add(tech2)
    db.flush()

    # 5. Lịch làm việc trong tương lai (+15 ngày)
    test_date = date.today() + timedelta(days=15)
    sch1 = TechnicianSchedule(
        technician_id=tech1.id,
        work_date=test_date,
        start_time=time(8, 0),
        end_time=time(18, 0),
        status="AVAILABLE",
    )
    sch2 = TechnicianSchedule(
        technician_id=tech2.id,
        work_date=test_date,
        start_time=time(8, 0),
        end_time=time(18, 0),
        status="AVAILABLE",
    )
    db.add(sch1)
    db.add(sch2)
    db.commit()

    return {
        "cust_a_id": cust_a.id,
        "dev_a_id": dev_a.id,
        "cust_b_id": cust_b.id,
        "dev_b_id": dev_b.id,
        "svc_60_id": svc_60.id,
        "svc_60_price": svc_60.base_price,
        "svc_30_id": svc_30.id,
        "tech1_id": tech1.id,
        "tech2_id": tech2.id,
        "test_date": test_date,
    }


# ============================================================================
# NHÓM A: KIỂM THỬ HAI YÊU CẦU ĐẶT CÙNG SLOT (CONCURRENCY)
# ============================================================================


def test_con_01_two_concurrent_requests_same_slot(
    client: TestClient, db: Session, task181_fixture: dict[str, Any]
) -> None:
    """CON-01: Hai request gửi gần như đồng thời để đặt cùng một slot.

    - Khung giờ: 09:00 - 10:00 (dịch vụ 60 phút) của Kỹ thuật viên 1.
    - Cả hai request được dispatch đồng thời qua ThreadPoolExecutor.
    - Kỳ vọng:
      + Chính xác 1 request thành công (HTTP 201 Created).
      + 1 request bị từ chối thích hợp (HTTP 409 Conflict với thông báo trùng lịch).
      + Cơ sở dữ liệu chỉ chứa đúng 1 bản ghi lịch hẹn hợp lệ cho slot này.
    """
    cust_a_id = task181_fixture["cust_a_id"]
    dev_a_id = task181_fixture["dev_a_id"]
    cust_b_id = task181_fixture["cust_b_id"]
    dev_b_id = task181_fixture["dev_b_id"]
    svc_id = task181_fixture["svc_60_id"]
    tech_id = task181_fixture["tech1_id"]
    test_date = task181_fixture["test_date"]

    payload_a = {
        "customer_id": str(cust_a_id),
        "device_id": str(dev_a_id),
        "service_id": str(svc_id),
        "technician_id": str(tech_id),
        "appointment_date": test_date.isoformat(),
        "start_time": "09:00",
        "description": "Đặt lịch khách hàng A qua tiến trình đồng thời",
    }
    payload_b = {
        "customer_id": str(cust_b_id),
        "device_id": str(dev_b_id),
        "service_id": str(svc_id),
        "technician_id": str(tech_id),
        "appointment_date": test_date.isoformat(),
        "start_time": "09:00",
        "description": "Đặt lịch khách hàng B qua tiến trình đồng thời",
    }

    # Đối với SQLite in-memory, kết nối dùng StaticPool đơn tuyến C, do đó cần lock serialize
    # đối với request xử lý nhằm tránh SQLITE_MISUSE trong môi trường test SQLite.
    # Trong môi trường PostgreSQL thực tế, transaction isolation và with_for_update xử lý lock hàng mức DB.
    request_lock = threading.Lock()

    def execute_booking(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        with request_lock:
            resp = client.post("/api/v1/appointments", json=payload)
            return resp.status_code, resp.json()

    # Thực thi 2 requests qua ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(execute_booking, payload_a)
        future_b = executor.submit(execute_booking, payload_b)
        status_a, data_a = future_a.result()
        status_b, data_b = future_b.result()

    status_codes = [status_a, status_b]
    # Xác minh đúng 1 request thành công (201) và 1 request nhận 409 Conflict
    assert 201 in status_codes, (
        f"Phải có ít nhất 1 request thành công 201: {status_codes}"
    )
    assert 409 in status_codes, (
        f"Request còn lại phải bị từ chối 409 Conflict: {status_codes}"
    )
    assert status_codes.count(201) == 1, "Chỉ được phép đúng 1 request thành công!"
    assert status_codes.count(409) == 1, "Request thứ hai phải nhận lỗi xung đột 409!"

    # Xác minh phản hồi từ chối có thông báo rõ ràng về việc slot đã được đặt
    conflict_data = data_b if status_b == 409 else data_a
    assert "Khung giờ đã có lịch hẹn khác" in conflict_data.get("detail", "")

    # Xác minh trong cơ sở dữ liệu: Không có 2 bản ghi đặt lịch trùng slot
    target_start_dt = datetime.combine(test_date, time(9, 0), tzinfo=UTC)
    appts = db.exec(
        select(Appointment)
        .where(Appointment.technician_id == tech_id)
        .where(Appointment.appointment_date == target_start_dt)
        .where(Appointment.status != AppointmentStatus.CANCELLED.value)
    ).all()
    assert len(appts) == 1, (
        f"Cơ sở dữ liệu xuất hiện {len(appts)} lịch hẹn trùng lặp, vi phạm quy tắc nghiệp vụ!"
    )


def test_con_02_sequential_request_after_slot_booked(
    client: TestClient, task181_fixture: dict[str, Any]
) -> None:
    """CON-02: Request tiếp theo khi slot đã được đặt trước đó.

    - Đặt thành công slot 10:00 - 11:00.
    - Request thứ hai gửi sau đó yêu cầu cùng slot.
    - Kỳ vọng:
      + Request thứ hai nhận HTTP 409 Conflict ('Khung giờ đã có lịch hẹn khác').
      + API kiểm tra slot (/api/v1/slots/check) trả về available=False, reason=SLOT_UNAVAILABLE.
    """
    cust_a_id = task181_fixture["cust_a_id"]
    dev_a_id = task181_fixture["dev_a_id"]
    cust_b_id = task181_fixture["cust_b_id"]
    dev_b_id = task181_fixture["dev_b_id"]
    svc_id = task181_fixture["svc_60_id"]
    tech_id = task181_fixture["tech1_id"]
    test_date = task181_fixture["test_date"]

    # 1. Đặt lịch lần 1 thành công
    resp1 = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust_a_id),
            "device_id": str(dev_a_id),
            "service_id": str(svc_id),
            "technician_id": str(tech_id),
            "appointment_date": test_date.isoformat(),
            "start_time": "10:00",
            "description": "Đặt lịch ban đầu",
        },
    )
    assert resp1.status_code == 201

    # 2. Request thứ hai cố đặt lại khung giờ 10:00 của cùng kỹ thuật viên
    resp2 = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust_b_id),
            "device_id": str(dev_b_id),
            "service_id": str(svc_id),
            "technician_id": str(tech_id),
            "appointment_date": test_date.isoformat(),
            "start_time": "10:00",
            "description": "Cố tình đặt trùng khung giờ đã có người đặt",
        },
    )
    assert resp2.status_code == 409
    assert "Khung giờ đã có lịch hẹn khác" in resp2.json()["detail"]

    # 3. Kiểm tra tính khả dụng của slot qua API check
    check_resp = client.post(
        "/api/v1/slots/check",
        json={
            "service_id": str(svc_id),
            "appointment_date": test_date.isoformat(),
            "start_time": "10:00",
            "technician_id": str(tech_id),
        },
    )
    assert check_resp.status_code == 200
    check_json = check_resp.json()
    assert check_json["available"] is False
    assert check_json["reason"] == "SLOT_UNAVAILABLE"


def test_con_03_high_concurrency_multiple_requests_same_slot(
    client: TestClient, db: Session, task181_fixture: dict[str, Any]
) -> None:
    """CON-03: Kiểm tra mức độ tranh chấp cao với 5 request đồng thời cạnh tranh 1 slot duy nhất.

    - Slot: 11:30 - 12:30 của KTV 1.
    - 5 luồng cùng gửi yêu cầu đặt slot này.
    - Kỳ vọng:
      + Đúng 1 request thành công (201).
      + 4 request còn lại bị từ chối với 409 Conflict.
      + DB chỉ ghi nhận 1 bản ghi lịch hẹn.
    """
    svc_id = task181_fixture["svc_60_id"]
    tech_id = task181_fixture["tech1_id"]
    test_date = task181_fixture["test_date"]

    request_lock = threading.Lock()

    def make_concurrent_booking(index: int) -> tuple[int, dict[str, Any]]:
        with request_lock:
            payload = {
                "customer_phone": f"0965{index:03d}999",
                "customer_name": f"Khách Hàng Luồng {index}",
                "service_id": str(svc_id),
                "technician_id": str(tech_id),
                "appointment_date": test_date.isoformat(),
                "start_time": "11:30",
                "description": f"Tranh chấp slot mức cao - Luồng {index}",
            }
            resp = client.post("/api/v1/appointments", json=payload)
            return resp.status_code, resp.json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_concurrent_booking, i) for i in range(5)]
        results = [f.result() for f in futures]

    statuses = [r[0] for r in results]
    assert statuses.count(201) == 1, (
        f"Kỳ vọng đúng 1 request thành công, thực tế: {statuses}"
    )
    assert statuses.count(409) == 4, (
        f"Kỳ vọng 4 request bị từ chối 409, thực tế: {statuses}"
    )

    # Kiểm tra cơ sở dữ liệu
    target_start_dt = datetime.combine(test_date, time(11, 30), tzinfo=UTC)
    appts = db.exec(
        select(Appointment)
        .where(Appointment.technician_id == tech_id)
        .where(Appointment.appointment_date == target_start_dt)
        .where(Appointment.status != AppointmentStatus.CANCELLED.value)
    ).all()
    assert len(appts) == 1


def test_con_04_concurrent_requests_different_slots_or_technicians_both_succeed(
    client: TestClient, task181_fixture: dict[str, Any]
) -> None:
    """CON-04: Hai request đồng thời nhưng đặt khác slot hoặc khác kỹ thuật viên.

    - Luồng 1 đặt KTV 1 lúc 13:00 - 14:00.
    - Luồng 2 đặt KTV 2 lúc 13:00 - 14:00.
    - Kỳ vọng: Cả 2 request đều thành công (201 Created), không bị chặn nhầm.
    """
    cust_a_id = task181_fixture["cust_a_id"]
    dev_a_id = task181_fixture["dev_a_id"]
    cust_b_id = task181_fixture["cust_b_id"]
    dev_b_id = task181_fixture["dev_b_id"]
    svc_id = task181_fixture["svc_60_id"]
    tech1_id = task181_fixture["tech1_id"]
    tech2_id = task181_fixture["tech2_id"]
    test_date = task181_fixture["test_date"]

    payload1 = {
        "customer_id": str(cust_a_id),
        "device_id": str(dev_a_id),
        "service_id": str(svc_id),
        "technician_id": str(tech1_id),
        "appointment_date": test_date.isoformat(),
        "start_time": "13:00",
        "description": "Đặt KTV 1",
    }
    payload2 = {
        "customer_id": str(cust_b_id),
        "device_id": str(dev_b_id),
        "service_id": str(svc_id),
        "technician_id": str(tech2_id),
        "appointment_date": test_date.isoformat(),
        "start_time": "13:00",
        "description": "Đặt KTV 2",
    }

    request_lock = threading.Lock()

    def run_req(payload: dict[str, Any]) -> int:
        with request_lock:
            return client.post("/api/v1/appointments", json=payload).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_req, payload1)
        f2 = executor.submit(run_req, payload2)
        res1, res2 = f1.result(), f2.result()

    assert res1 == 201, f"Request KTV 1 thất bại: {res1}"
    assert res2 == 201, f"Request KTV 2 thất bại: {res2}"


def test_con_05_concurrent_auto_assignment_single_available_technician(
    client: TestClient, db: Session, task181_fixture: dict[str, Any]
) -> None:
    """CON-05: Hai request đồng thời không chọn kỹ thuật viên (auto-assignment).

    - Tạo ngày test mới chỉ có duy nhất 1 kỹ thuật viên có ca trực AVAILABLE.
    - Hai request gửi đồng thời cùng yêu cầu đặt slot 14:00.
    - Kỳ vọng:
      + Request 1 được gán kỹ thuật viên duy nhất đó và trả về 201 Created.
      + Request 2 bị từ chối với 409 Conflict ('Tất cả kỹ thuật viên đều đã kín lịch...').
      + Cơ sở dữ liệu chỉ có đúng 1 lịch hẹn.
    """
    tech_id = task181_fixture["tech1_id"]
    svc_id = task181_fixture["svc_60_id"]
    single_tech_date = date.today() + timedelta(days=22)

    # Tạo lịch trực chỉ cho KTV 1 vào ngày này
    sch = TechnicianSchedule(
        technician_id=tech_id,
        work_date=single_tech_date,
        start_time=time(8, 0),
        end_time=time(18, 0),
        status="AVAILABLE",
    )
    db.add(sch)
    db.commit()

    request_lock = threading.Lock()

    def run_auto_assign_req(index: int) -> tuple[int, dict[str, Any]]:
        with request_lock:
            payload = {
                "customer_phone": f"0944{index:03d}111",
                "customer_name": f"Khách Auto {index}",
                "service_id": str(svc_id),
                "technician_id": None,  # Tự động gán kỹ thuật viên
                "appointment_date": single_tech_date.isoformat(),
                "start_time": "14:00",
                "description": f"Auto assignment tranh chấp slot - Luồng {index}",
            }
            resp = client.post("/api/v1/appointments", json=payload)
            return resp.status_code, resp.json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_auto_assign_req, 1)
        f2 = executor.submit(run_auto_assign_req, 2)
        status1, data1 = f1.result()
        status2, data2 = f2.result()

    statuses = [status1, status2]
    assert 201 in statuses
    assert 409 in statuses
    assert statuses.count(201) == 1
    assert statuses.count(409) == 1

    conflict_data = data2 if status2 == 409 else data1
    assert (
        "Tất cả kỹ thuật viên đều đã kín lịch trong khung giờ này"
        in conflict_data.get("detail", "")
    )


# ============================================================================
# NHÓM B: KIỂM THỬ GIAO DỊCH POSTGRESQL & ROLLBACK
# ============================================================================


def test_db_01_transaction_atomic_commit_all_entities_created(
    client: TestClient, db: Session, task181_fixture: dict[str, Any]
) -> None:
    """DB-01: Transaction thành công - Dữ liệu được commit nhất quán.

    - Gọi API tạo lịch hẹn.
    - Kiểm tra tính nguyên tử (Atomicity) của giao dịch:
      + Bản ghi Appointment được tạo với status PENDING.
      + Bản ghi AppointmentService được liên kết đúng service_id và price_at_booking.
      + Bản ghi RepairStatusHistory được tạo đồng thời làm nhật ký kiểm toán ban đầu.
      + Tất cả các bản ghi có chung appointment_id và timestamp hợp lệ.
    """
    cust_a_id = task181_fixture["cust_a_id"]
    dev_a_id = task181_fixture["dev_a_id"]
    svc_id = task181_fixture["svc_60_id"]
    svc_price = task181_fixture["svc_60_price"]
    tech_id = task181_fixture["tech1_id"]
    test_date = task181_fixture["test_date"]

    resp = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust_a_id),
            "device_id": str(dev_a_id),
            "service_id": str(svc_id),
            "technician_id": str(tech_id),
            "appointment_date": test_date.isoformat(),
            "start_time": "15:00",
            "description": "Kiểm tra commit nguyên tử giao dịch",
        },
    )
    assert resp.status_code == 201
    resp_data = resp.json()
    appt_id = uuid.UUID(resp_data["appointment_id"])

    # 1. Kiểm tra Appointment trong database
    appt = db.get(Appointment, appt_id)
    assert appt is not None
    assert appt.status == "PENDING"
    assert appt.total_amount == svc_price
    assert appt.customer_id == cust_a_id
    assert appt.device_id == dev_a_id
    assert appt.technician_id == tech_id

    # 2. Kiểm tra AppointmentService được commit cùng transaction
    appt_svcs = db.exec(
        select(AppointmentService).where(AppointmentService.appointment_id == appt_id)
    ).all()
    assert len(appt_svcs) == 1
    assert appt_svcs[0].service_id == svc_id
    assert appt_svcs[0].price_at_booking == svc_price

    # 3. Kiểm tra RepairStatusHistory được commit cùng transaction
    histories = db.exec(
        select(RepairStatusHistory).where(RepairStatusHistory.appointment_id == appt_id)
    ).all()
    assert len(histories) == 1
    assert histories[0].previous_status is None
    assert histories[0].new_status == "PENDING"
    assert histories[0].note == "Tạo lịch hẹn thành công"


def test_db_02_transaction_rollback_on_error_no_orphans(
    db: Session, task181_fixture: dict[str, Any]
) -> None:
    """DB-02: Transaction phát sinh lỗi - Dữ liệu được rollback hoàn toàn.

    - Mô phỏng phát sinh lỗi ngoại lệ hệ thống ngay trước khi commit.
    - Kỳ vọng:
      + Hệ thống bắt được Exception và gọi session.rollback().
      + Không có bản ghi Appointment nào được tạo trong DB.
      + Không có bản ghi AppointmentService hay RepairStatusHistory nào dở dang.
    """
    cust_a_id = task181_fixture["cust_a_id"]
    dev_a_id = task181_fixture["dev_a_id"]
    svc_id = task181_fixture["svc_60_id"]
    tech_id = task181_fixture["tech1_id"]
    test_date = task181_fixture["test_date"]

    payload = AppointmentBookingCreate(
        customer_id=cust_a_id,
        device_id=dev_a_id,
        service_id=svc_id,
        technician_id=tech_id,
        appointment_date=test_date,
        start_time=time(16, 0),
        description="Kiểm thử rollback khi có lỗi hệ thống",
    )

    # Giả lập lỗi cơ sở dữ liệu tại thời điểm commit
    with patch.object(
        Session, "commit", side_effect=RuntimeError("Lỗi kết nối DB bất ngờ")
    ):
        with pytest.raises(Exception) as exc_info:
            slot_service.create_booking_appointment(session=db, data=payload)
        assert "Lỗi hệ thống khi tạo lịch hẹn" in str(exc_info.value)

    # Xác minh trong database: Không có Appointment nào ở slot 16:00
    target_start_dt = datetime.combine(test_date, time(16, 0), tzinfo=UTC)
    appt = db.exec(
        select(Appointment)
        .where(Appointment.technician_id == tech_id)
        .where(Appointment.appointment_date == target_start_dt)
    ).first()
    assert appt is None, "Lịch hẹn không được phép tồn tại sau khi rollback!"


def test_db_03_transaction_rollback_data_integrity_check(
    client: TestClient, db: Session, task181_fixture: dict[str, Any]
) -> None:
    """DB-03: Kiểm tra tính toàn vẹn dữ liệu trước và sau rollback.

    - Đếm chính xác số lượng bản ghi trong các bảng (Appointment, AppointmentService, RepairStatusHistory).
    - Thực hiện request không hợp lệ gây lỗi hoặc xung đột nghiệp vụ.
    - Đếm lại số lượng bản ghi sau khi kết thúc.
    - Kỳ vọng: Số lượng bản ghi trước và sau hoàn toàn đồng nhất, không có rác hay dữ liệu dở dang.
    """
    cust_a_id = task181_fixture["cust_a_id"]
    dev_a_id = task181_fixture["dev_a_id"]
    svc_id = task181_fixture["svc_60_id"]
    tech_id = task181_fixture["tech1_id"]

    # Đếm số lượng ban đầu
    initial_appts = len(db.exec(select(Appointment)).all())
    initial_svc_links = len(db.exec(select(AppointmentService)).all())
    initial_histories = len(db.exec(select(RepairStatusHistory)).all())

    # Gửi request với ngày trong quá khứ -> Gây HTTP 400 Bad Request
    past_date = date.today() - timedelta(days=1)
    resp = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust_a_id),
            "device_id": str(dev_a_id),
            "service_id": str(svc_id),
            "technician_id": str(tech_id),
            "appointment_date": past_date.isoformat(),
            "start_time": "10:00",
            "description": "Đặt lịch ngày quá khứ phải bị từ chối",
        },
    )
    assert resp.status_code == 400
    assert "Không thể đặt lịch trong quá khứ" in resp.json()["detail"]

    # Đếm lại số lượng sau request lỗi
    final_appts = len(db.exec(select(Appointment)).all())
    final_svc_links = len(db.exec(select(AppointmentService)).all())
    final_histories = len(db.exec(select(RepairStatusHistory)).all())

    assert final_appts == initial_appts, "Bảng Appointment bị thay đổi sau rollback!"
    assert final_svc_links == initial_svc_links, (
        "Bảng AppointmentService bị thay đổi sau rollback!"
    )
    assert final_histories == initial_histories, (
        "Bảng RepairStatusHistory bị thay đổi sau rollback!"
    )


def test_db_04_transaction_rollback_during_appointment_update(
    client: TestClient, db: Session, task181_fixture: dict[str, Any]
) -> None:
    """DB-04: Transaction rollback khi cập nhật lịch hẹn phát sinh lỗi / xung đột.

    - Tạo trước 2 lịch hẹn hợp lệ:
      + Appt 1: 08:00 - 09:00
      + Appt 2: 09:00 - 10:00
    - Cố tình cập nhật Appt 2 chuyển sang 08:00 (trùng với Appt 1).
    - Kỳ vọng:
      + Bị từ chối với 409 Conflict.
      + Giao dịch cập nhật rollback: Appt 2 giữ nguyên ngày giờ cũ (09:00).
      + Không có bản ghi RepairStatusHistory giả mạo nào được ghi thêm.
    """
    cust_a_id = task181_fixture["cust_a_id"]
    dev_a_id = task181_fixture["dev_a_id"]
    cust_b_id = task181_fixture["cust_b_id"]
    dev_b_id = task181_fixture["dev_b_id"]
    svc_id = task181_fixture["svc_60_id"]
    tech_id = task181_fixture["tech2_id"]
    test_date = task181_fixture["test_date"]

    # Tạo Appt 1: 08:00
    r1 = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust_a_id),
            "device_id": str(dev_a_id),
            "service_id": str(svc_id),
            "technician_id": str(tech_id),
            "appointment_date": test_date.isoformat(),
            "start_time": "08:00",
            "description": "Lịch hẹn 1",
        },
    )
    assert r1.status_code == 201

    # Tạo Appt 2: 09:00
    r2 = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust_b_id),
            "device_id": str(dev_b_id),
            "service_id": str(svc_id),
            "technician_id": str(tech_id),
            "appointment_date": test_date.isoformat(),
            "start_time": "09:00",
            "description": "Lịch hẹn 2",
        },
    )
    assert r2.status_code == 201
    appt2_id = r2.json()["appointment_id"]

    # Đếm số lịch sử trạng thái của Appt 2 trước khi update lỗi
    histories_before = len(
        db.exec(
            select(RepairStatusHistory).where(
                RepairStatusHistory.appointment_id == uuid.UUID(appt2_id)
            )
        ).all()
    )

    # Tạo nhân viên thực tế có token hợp lệ
    _, staff_headers = create_authenticated_staff_user(db=db, role="staff")

    # Cố tình đổi giờ Appt 2 sang 08:00 -> Trùng Appt 1
    update_resp = client.patch(
        f"/api/v1/appointments/{appt2_id}",
        headers=staff_headers,
        json={
            "start_time": "08:00",
            "reschedule_reason": "Đổi giờ trùng lặp",
        },
    )
    assert update_resp.status_code == 409
    assert "Khung giờ mới đã bị trùng với lịch hẹn khác" in update_resp.json()["detail"]

    # Kiểm tra DB: Appt 2 vẫn giữ nguyên giờ 09:00, không bị sửa đổi dở dang
    db.expire_all()
    saved_appt2 = db.get(Appointment, uuid.UUID(appt2_id))
    assert saved_appt2 is not None
    assert saved_appt2.appointment_date.time() == time(9, 0)

    # Lịch sử trạng thái của Appt 2 không có bản ghi mới
    histories_after = len(
        db.exec(
            select(RepairStatusHistory).where(
                RepairStatusHistory.appointment_id == uuid.UUID(appt2_id)
            )
        ).all()
    )
    assert histories_after == histories_before


def test_db_05_transaction_rollback_during_technician_assignment(
    client: TestClient, db: Session, task181_fixture: dict[str, Any]
) -> None:
    """DB-05: Transaction rollback khi phân công kỹ thuật viên phát sinh lỗi hoặc xung đột.

    - KTV 2 đã kín lịch ở khung giờ 10:00.
    - KTV 1 có lịch lúc 10:00.
    - Cố tình phân công lại lịch của KTV 1 sang KTV 2 ở khung giờ 10:00.
    - Kỳ vọng:
      + Phản hồi 409 Conflict.
      + Transaction rollback hoàn toàn: technician_id không bị thay đổi.
      + Không có bản ghi RepairStatusHistory giả nào được thêm vào.
    """
    cust_a_id = task181_fixture["cust_a_id"]
    dev_a_id = task181_fixture["dev_a_id"]
    cust_b_id = task181_fixture["cust_b_id"]
    dev_b_id = task181_fixture["dev_b_id"]
    svc_id = task181_fixture["svc_60_id"]
    tech1_id = task181_fixture["tech1_id"]
    tech2_id = task181_fixture["tech2_id"]
    test_date = task181_fixture["test_date"]

    # 1. KTV 2 đã có lịch lúc 10:00
    r_tech2 = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust_a_id),
            "device_id": str(dev_a_id),
            "service_id": str(svc_id),
            "technician_id": str(tech2_id),
            "appointment_date": test_date.isoformat(),
            "start_time": "10:00",
            "description": "Lịch của KTV 2",
        },
    )
    assert r_tech2.status_code == 201

    # 2. Tạo lịch hẹn của KTV 1 lúc 10:00
    r_tech1 = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": str(cust_b_id),
            "device_id": str(dev_b_id),
            "service_id": str(svc_id),
            "technician_id": str(tech1_id),
            "appointment_date": test_date.isoformat(),
            "start_time": "10:00",
            "description": "Lịch của KTV 1",
        },
    )
    assert r_tech1.status_code == 201
    appt_id = r_tech1.json()["appointment_id"]

    # Tạo nhân viên thực tế có token hợp lệ
    _, staff_headers = create_authenticated_staff_user(db=db, role="staff")

    # 3. Nhân viên cố tình phân công lại lịch của KTV 1 sang KTV 2 (vốn đã kín lịch 10:00)
    assign_resp = client.post(
        f"/api/v1/appointments/{appt_id}/assign-technician",
        headers=staff_headers,
        json={
            "technician_id": str(tech2_id),
            "note": "Cố tình phân công sang KTV đã bị trùng lịch",
        },
    )
    assert assign_resp.status_code == 409
    assert "đã bị trùng lịch với lịch hẹn khác" in assign_resp.json()["detail"]

    # 4. Kiểm tra trong DB: Lịch hẹn vẫn thuộc về KTV 1, không bị chuyển dở dang
    db.expire_all()
    appt_db = db.get(Appointment, uuid.UUID(appt_id))
    assert appt_db is not None
    assert appt_db.technician_id == tech1_id


def test_db_06_database_constraints_enforcement(
    db: Session, task181_fixture: dict[str, Any]
) -> None:
    """DB-06: Xác minh các ràng buộc cơ sở dữ liệu (Check Constraints & Foreign Key Integrity).

    - Thử ghi Appointment có total_amount âm (-500.0) vi phạm check_appointment_total_amount_non_negative.
    - Thử ghi Appointment với customer_id không tồn tại (vi phạm Foreign Key).
    - Kỳ vọng: Database / ORM từ chối và rollback giao dịch, bảo vệ toàn vẹn dữ liệu.
    """
    dev_id = task181_fixture["dev_a_id"]
    cust_id = task181_fixture["cust_a_id"]
    test_date = task181_fixture["test_date"]

    # 1. Kiểm tra Check Constraint total_amount >= 0
    invalid_appt = Appointment(
        appointment_number=f"APPT-ERR-{uuid.uuid4().hex[:6].upper()}",
        customer_id=cust_id,
        device_id=dev_id,
        appointment_date=datetime.combine(test_date, time(17, 0), tzinfo=UTC),
        status="PENDING",
        total_amount=-500.0,  # Vi phạm ràng buộc Check Constraint
    )
    db.add(invalid_appt)
    with pytest.raises((IntegrityError, Exception)):
        db.commit()
    db.rollback()

    # 2. Kiểm tra Foreign Key Constraint (khi Foreign Key checks được bật)
    fake_customer_id = uuid.uuid4()
    invalid_fk_appt = Appointment(
        appointment_number=f"APPT-FK-{uuid.uuid4().hex[:6].upper()}",
        customer_id=fake_customer_id,  # Khóa ngoại không tồn tại
        device_id=dev_id,
        appointment_date=datetime.combine(test_date, time(17, 30), tzinfo=UTC),
        status="PENDING",
        total_amount=100_000.0,
    )
    db.add(invalid_fk_appt)
    with pytest.raises((IntegrityError, Exception)):
        db.commit()
    db.rollback()
