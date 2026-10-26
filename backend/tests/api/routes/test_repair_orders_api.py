import uuid
from datetime import UTC, date, datetime, time

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import security
from app.crud import create_user
from app.models import (
    Appointment,
    AppointmentStatus,
    Customer,
    Device,
    RepairStatusHistory,
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


def setup_repair_fixture(db: Session) -> dict[str, object]:
    cust = Customer(
        full_name="Nguyễn Văn An",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
        email=random_email(),
    )
    db.add(cust)
    db.commit()

    device = Device(
        customer_id=cust.id,
        brand="Apple",
        model="iPhone 14 Pro",
        imei=f"356{uuid.uuid4().int % 1000000000000:012d}",
        serial_number=f"F2L{uuid.uuid4().hex[:8].upper()}",
    )
    db.add(device)
    db.commit()

    tech1 = Technician(
        full_name="Kỹ Thuật Viên Minh",
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
        specialization="Màn hình, Ép kính",
        is_active=True,
    )
    tech2 = Technician(
        full_name="Kỹ Thuật Viên Đức",
        phone_number=f"097{uuid.uuid4().int % 10000000:07d}",
        specialization="Phần cứng, Mainboard",
        is_active=True,
    )
    inactive_tech = Technician(
        full_name="Kỹ Thuật Viên Nghỉ Việc",
        phone_number=f"093{uuid.uuid4().int % 10000000:07d}",
        is_active=False,
    )
    off_tech = Technician(
        full_name="Kỹ Thuật Viên Nghỉ Phép",
        phone_number=f"092{uuid.uuid4().int % 10000000:07d}",
        is_active=True,
    )
    db.add(tech1)
    db.add(tech2)
    db.add(inactive_tech)
    db.add(off_tech)
    db.commit()

    # Tạo lịch nghỉ phép cho off_tech trong ngày hôm nay
    today = date.today()
    schedule_off = TechnicianSchedule(
        technician_id=off_tech.id,
        work_date=today,
        start_time=time(8, 0),
        end_time=time(17, 0),
        status="OFF",
    )
    db.add(schedule_off)

    appt = Appointment(
        appointment_number=f"APPT-{uuid.uuid4().hex[:8].upper()}",
        appointment_date=datetime.now(UTC),
        status=AppointmentStatus.PENDING.value,
        device_id=device.id,
        customer_id=cust.id,
        cancellation_reason=None,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    return {
        "customer": cust,
        "device": device,
        "tech1": tech1,
        "tech2": tech2,
        "inactive_tech": inactive_tech,
        "off_tech": off_tech,
        "appointment": appt,
    }


# ==============================================================================
# CHỨC NĂNG B: CẬP NHẬT TRẠNG THÁI SỬA CHỮA (Update Repair Status)
# ==============================================================================


def test_update_repair_status_valid_flow(client: TestClient, db: Session) -> None:
    """Test chu trình chuyển trạng thái hợp lệ: PENDING -> CONFIRMED -> IN_PROGRESS -> COMPLETED."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    # 1. PENDING -> CONFIRMED
    res1 = client.patch(
        f"/api/v1/repair-orders/{appt.id}/status",
        headers=headers,
        json={"status": "CONFIRMED", "note": "Đã tiếp nhận máy và xác nhận"},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["success"] is True
    assert data1["data"]["previous_status"] == "PENDING"
    assert data1["data"]["current_status"] == "CONFIRMED"

    # Kiểm tra bản ghi lịch sử trong DB
    histories = db.exec(
        select(RepairStatusHistory).where(RepairStatusHistory.appointment_id == appt.id)
    ).all()
    assert len(histories) == 1
    assert histories[0].previous_status == "PENDING"
    assert histories[0].new_status == "CONFIRMED"
    assert histories[0].changed_by_user_id == staff.id

    # 2. CONFIRMED -> IN_PROGRESS
    res2 = client.patch(
        f"/api/v1/repair-orders/{appt.id}/status",
        headers=headers,
        json={
            "status": "IN_PROGRESS",
            "technician_diagnosis": "Hỏng màn hình OLED, cần thay cụm màn mới",
            "note": "Bắt đầu bóc tách máy và thay thế",
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["data"]["current_status"] == "IN_PROGRESS"
    assert (
        data2["data"]["technician_diagnosis"]
        == "Hỏng màn hình OLED, cần thay cụm màn mới"
    )

    # 3. IN_PROGRESS -> COMPLETED
    res3 = client.patch(
        f"/api/v1/repair-orders/{appt.id}/status",
        headers=headers,
        json={"status": "COMPLETED", "note": "Đã test các chức năng OK"},
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["data"]["current_status"] == "COMPLETED"
    assert data3["data"]["actual_completion_date"] is not None

    db.refresh(appt)
    assert appt.status == "COMPLETED"
    assert appt.actual_completion_date is not None


def test_update_repair_status_cancellation(client: TestClient, db: Session) -> None:
    """Test cập nhật trạng thái CANCELLED kèm cancellation_reason."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    res = client.patch(
        f"/api/v1/repair-orders/{appt.id}/status",
        headers=headers,
        json={
            "status": "CANCELLED",
            "cancellation_reason": "Khách không đồng ý chi phí thay linh kiện",
            "note": "Hủy phiếu sửa chữa theo yêu cầu khách",
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["current_status"] == "CANCELLED"

    db.refresh(appt)
    assert appt.status == "CANCELLED"
    assert appt.cancellation_reason == "Khách không đồng ý chi phí thay linh kiện"


def test_update_repair_status_same_status_bad_request(
    client: TestClient, db: Session
) -> None:
    """Chặn chuyển sang chính trạng thái hiện tại (400 Bad Request)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    res = client.patch(
        f"/api/v1/repair-orders/{appt.id}/status",
        headers=headers,
        json={"status": "PENDING", "note": "Giữ nguyên"},
    )
    assert res.status_code == 400
    assert "đã ở trạng thái" in res.json()["detail"]


def test_update_repair_status_invalid_jump_bad_request(
    client: TestClient, db: Session
) -> None:
    """Chặn chuyển từ PENDING thẳng sang COMPLETED khi chưa qua tiếp nhận/sửa chữa."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    res = client.patch(
        f"/api/v1/repair-orders/{appt.id}/status",
        headers=headers,
        json={"status": "COMPLETED", "note": "Nhảy cóc"},
    )
    assert res.status_code == 400
    assert "cần được tiếp nhận và xử lý" in res.json()["detail"]


def test_update_repair_status_already_finished_conflict(
    client: TestClient, db: Session
) -> None:
    """Chặn cập nhật khi phiếu sửa chữa đã COMPLETED hoặc CANCELLED (409 Conflict)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    appt.status = "COMPLETED"
    db.add(appt)
    db.commit()

    res = client.patch(
        f"/api/v1/repair-orders/{appt.id}/status",
        headers=headers,
        json={"status": "IN_PROGRESS"},
    )
    assert res.status_code == 409
    assert "đã kết thúc" in res.json()["detail"]


def test_update_repair_status_not_found(client: TestClient, db: Session) -> None:
    """Kiểm tra 404 khi repair_order_id không tồn tại."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fake_id = uuid.uuid4()

    res = client.patch(
        f"/api/v1/repair-orders/{fake_id}/status",
        headers=headers,
        json={"status": "CONFIRMED"},
    )
    assert res.status_code == 404


def test_update_repair_status_invalid_enum(client: TestClient, db: Session) -> None:
    """Kiểm tra Pydantic validation (422) khi gửi trạng thái không thuộc enum."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    res = client.patch(
        f"/api/v1/repair-orders/{appt.id}/status",
        headers=headers,
        json={"status": "NOT_A_VALID_STATUS"},
    )
    assert res.status_code == 422


def test_update_repair_status_permissions(client: TestClient, db: Session) -> None:
    """Kiểm tra phân quyền: customer bị 403, không token bị 401."""
    customer_user = create_role_user(db, "customer")
    cust_headers = get_token_headers(customer_user)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    # 1. Customer
    res1 = client.patch(
        f"/api/v1/repair-orders/{appt.id}/status",
        headers=cust_headers,
        json={"status": "CONFIRMED"},
    )
    assert res1.status_code == 403

    # 2. Không token
    res2 = client.patch(
        f"/api/v1/repair-orders/{appt.id}/status",
        json={"status": "CONFIRMED"},
    )
    assert res2.status_code == 401


def test_update_repair_status_transaction_rollback_on_error(
    monkeypatch, client: TestClient, db: Session
) -> None:
    """Kiểm tra transaction rollback khi xảy ra lỗi trong quá trình ghi dữ liệu: trạng thái không bị thay đổi dở dang."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    original_commit = Session.commit

    def failing_commit(_self: Session) -> None:
        raise RuntimeError("Database connection lost during commit")

    monkeypatch.setattr(Session, "commit", failing_commit)

    res = client.patch(
        f"/api/v1/repair-orders/{appt.id}/status",
        headers=headers,
        json={"status": "CONFIRMED", "note": "Thử nghiệm lỗi rollback"},
    )
    assert res.status_code == 500
    assert (
        "Đã xảy ra lỗi trong quá trình cập nhật trạng thái sửa chữa"
        in res.json()["detail"]
    )

    # Khôi phục commit và kiểm tra trạng thái trong DB vẫn là PENDING
    monkeypatch.setattr(Session, "commit", original_commit)
    db.expire_all()
    fresh_appt = db.get(Appointment, appt.id)
    assert fresh_appt is not None
    assert fresh_appt.status == "PENDING"


def test_repair_orders_alias_endpoints(client: TestClient, db: Session) -> None:
    """Kiểm tra alias endpoint /api/repair-orders/... hoạt động đồng bộ với /api/v1/repair-orders/..."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)

    # Alias /api/repair-orders/{id}/status
    res_status = client.patch(
        f"/api/repair-orders/{appt.id}/status",
        headers=headers,
        json={"status": "CONFIRMED", "note": "Test alias status"},
    )
    assert res_status.status_code == 200
    assert res_status.json()["data"]["current_status"] == "CONFIRMED"

    # Alias /api/repair-orders/{id}/technician
    res_tech = client.patch(
        f"/api/repair-orders/{appt.id}/technician",
        headers=headers,
        json={"technician_id": str(tech1.id), "note": "Test alias technician"},
    )
    assert res_tech.status_code == 200
    assert res_tech.json()["data"]["technician_id"] == str(tech1.id)


# ==============================================================================
# CHỨC NĂNG C: PHÂN CÔNG KỸ THUẬT VIÊN (Assign Technician)
# ==============================================================================


def test_assign_technician_success(client: TestClient, db: Session) -> None:
    """Test phân công kỹ thuật viên thành công (Assign Technician)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)

    res = client.patch(
        f"/api/v1/repair-orders/{appt.id}/technician",
        headers=headers,
        json={"technician_id": str(tech1.id), "note": "Phân công xử lý gấp"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["technician_id"] == str(tech1.id)
    assert data["data"]["technician_name"] == tech1.full_name

    db.refresh(appt)
    assert appt.technician_id == tech1.id

    # Kiểm tra ghi nhận lịch sử audit log
    histories = db.exec(
        select(RepairStatusHistory).where(RepairStatusHistory.appointment_id == appt.id)
    ).all()
    assert len(histories) >= 1
    last_history = histories[-1]
    assert tech1.full_name in last_history.note
    assert "Phân công xử lý gấp" in last_history.note
    assert last_history.changed_by_user_id == staff.id


def test_reassign_technician_success(client: TestClient, db: Session) -> None:
    """Test thay đổi kỹ thuật viên khi phiếu đã có người phụ trách."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    tech2 = fix["tech2"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)
    assert isinstance(tech2, Technician)

    # Gán tech1 trước
    appt.technician_id = tech1.id
    db.add(appt)
    db.commit()

    # Chuyển sang tech2
    res = client.patch(
        f"/api/v1/repair-orders/{appt.id}/technician",
        headers=headers,
        json={"technician_id": str(tech2.id), "note": "Đổi sang thợ cứng bo mạch"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["technician_id"] == str(tech2.id)
    assert data["technician_name"] == tech2.full_name

    db.refresh(appt)
    assert appt.technician_id == tech2.id

    # Kiểm tra note ghi rõ thay đổi từ tech1 sang tech2
    histories = db.exec(
        select(RepairStatusHistory).where(RepairStatusHistory.appointment_id == appt.id)
    ).all()
    last_history = histories[-1]
    assert f"từ {tech1.full_name} sang {tech2.full_name}" in last_history.note


def test_assign_technician_not_found(client: TestClient, db: Session) -> None:
    """Kiểm tra 404 khi không tìm thấy phiếu hoặc kỹ thuật viên."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)

    # 1. Phiếu không tồn tại
    fake_appt_id = uuid.uuid4()
    res1 = client.patch(
        f"/api/v1/repair-orders/{fake_appt_id}/technician",
        headers=headers,
        json={"technician_id": str(tech1.id)},
    )
    assert res1.status_code == 404

    # 2. Kỹ thuật viên không tồn tại
    fake_tech_id = uuid.uuid4()
    res2 = client.patch(
        f"/api/v1/repair-orders/{appt.id}/technician",
        headers=headers,
        json={"technician_id": str(fake_tech_id)},
    )
    assert res2.status_code == 404


def test_assign_technician_inactive_or_off(client: TestClient, db: Session) -> None:
    """Chặn phân công kỹ thuật viên đã nghỉ việc hoặc có lịch nghỉ trong ngày (400 Bad Request)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    inactive_tech = fix["inactive_tech"]
    off_tech = fix["off_tech"]
    assert isinstance(appt, Appointment)
    assert isinstance(inactive_tech, Technician)
    assert isinstance(off_tech, Technician)

    # 1. Kỹ thuật viên không hoạt động
    res1 = client.patch(
        f"/api/v1/repair-orders/{appt.id}/technician",
        headers=headers,
        json={"technician_id": str(inactive_tech.id)},
    )
    assert res1.status_code == 400
    assert "không hoạt động hoặc đã nghỉ việc" in res1.json()["detail"]

    # 2. Kỹ thuật viên đăng ký nghỉ (OFF) hôm nay
    res2 = client.patch(
        f"/api/v1/repair-orders/{appt.id}/technician",
        headers=headers,
        json={"technician_id": str(off_tech.id)},
    )
    assert res2.status_code == 400
    assert "đã đăng ký nghỉ (OFF)" in res2.json()["detail"]


def test_assign_technician_finished_appointment_conflict(
    client: TestClient, db: Session
) -> None:
    """Chặn phân công kỹ thuật viên cho phiếu sửa chữa đã kết thúc (409 Conflict)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)

    appt.status = "COMPLETED"
    db.add(appt)
    db.commit()

    res = client.patch(
        f"/api/v1/repair-orders/{appt.id}/technician",
        headers=headers,
        json={"technician_id": str(tech1.id)},
    )
    assert res.status_code == 409
    assert "đã kết thúc" in res.json()["detail"]


def test_assign_technician_permissions(client: TestClient, db: Session) -> None:
    """Kiểm tra phân quyền: customer bị 403, không token bị 401."""
    customer_user = create_role_user(db, "customer")
    cust_headers = get_token_headers(customer_user)
    fix = setup_repair_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)

    # 1. Customer
    res1 = client.patch(
        f"/api/v1/repair-orders/{appt.id}/technician",
        headers=cust_headers,
        json={"technician_id": str(tech1.id)},
    )
    assert res1.status_code == 403

    # 2. Không token
    res2 = client.patch(
        f"/api/v1/repair-orders/{appt.id}/technician",
        json={"technician_id": str(tech1.id)},
    )
    assert res2.status_code == 401
