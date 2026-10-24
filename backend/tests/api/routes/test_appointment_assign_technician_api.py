import uuid
from datetime import UTC, date, datetime, time, timedelta

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
    RepairStatusHistory,
    Service,
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


def setup_appointment_assign_fixture(db: Session) -> dict[str, object]:
    cust = Customer(
        full_name="Đặng Văn Lâm",
        phone_number=f"093{uuid.uuid4().int % 10000000:07d}",
        email=random_email(),
    )
    db.add(cust)
    db.commit()

    device = Device(
        customer_id=cust.id,
        brand="Apple",
        model="iPhone 14 Pro Max",
        imei=f"356{uuid.uuid4().int % 1000000000000:012d}",
        serial_number=f"F2L{uuid.uuid4().hex[:8].upper()}",
    )
    db.add(device)
    db.commit()

    # Dịch vụ thay màn hình (thời lượng 60 phút)
    svc_screen = Service(
        name=f"Thay màn hình iPhone {uuid.uuid4().hex[:4]}",
        base_price=2_000_000.0,
        estimated_duration_minutes=60,
        is_active=True,
    )
    db.add(svc_screen)
    db.commit()

    target_date = date.today() + timedelta(days=7)
    appt_datetime = datetime.combine(target_date, time(9, 0), tzinfo=UTC)

    # Kỹ thuật viên 1: Chuyên môn màn hình, có lịch làm việc AVAILABLE 08:00 - 17:00
    tech1 = Technician(
        full_name="Kỹ Thuật Viên Tuấn Màn Hình",
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
        specialization="Màn hình, Ép kính",
        is_active=True,
    )
    # Kỹ thuật viên 2: Chuyên môn màn hình & phần cứng, có lịch làm việc AVAILABLE 08:00 - 17:00
    tech2 = Technician(
        full_name="Kỹ Thuật Viên Hùng Phần Cứng",
        phone_number=f"097{uuid.uuid4().int % 10000000:07d}",
        specialization="Màn hình, Phần cứng",
        is_active=True,
    )
    # Kỹ thuật viên 3: Chuyên môn phần mềm (không khớp với dịch vụ màn hình)
    tech_software = Technician(
        full_name="Kỹ Thuật Viên Phần Mềm",
        phone_number=f"096{uuid.uuid4().int % 10000000:07d}",
        specialization="Chuyên phần mềm, Unlock",
        is_active=True,
    )
    # Kỹ thuật viên nghỉ việc
    tech_inactive = Technician(
        full_name="Kỹ Thuật Viên Đã Nghỉ",
        phone_number=f"094{uuid.uuid4().int % 10000000:07d}",
        is_active=False,
    )
    # Kỹ thuật viên nghỉ phép (OFF) vào target_date
    tech_off = Technician(
        full_name="Kỹ Thuật Viên Nghỉ Phép",
        phone_number=f"092{uuid.uuid4().int % 10000000:07d}",
        specialization="Màn hình",
        is_active=True,
    )
    # Kỹ thuật viên ca sáng (08:00 - 12:00)
    tech_morning_only = Technician(
        full_name="Kỹ Thuật Viên Ca Sáng",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
        specialization="Màn hình",
        is_active=True,
    )

    db.add(tech1)
    db.add(tech2)
    db.add(tech_software)
    db.add(tech_inactive)
    db.add(tech_off)
    db.add(tech_morning_only)
    db.commit()

    # Thêm ca làm việc
    sch1 = TechnicianSchedule(
        technician_id=tech1.id,
        work_date=target_date,
        start_time=time(8, 0),
        end_time=time(17, 0),
        status="AVAILABLE",
    )
    sch2 = TechnicianSchedule(
        technician_id=tech2.id,
        work_date=target_date,
        start_time=time(8, 0),
        end_time=time(17, 0),
        status="AVAILABLE",
    )
    sch_software = TechnicianSchedule(
        technician_id=tech_software.id,
        work_date=target_date,
        start_time=time(8, 0),
        end_time=time(17, 0),
        status="AVAILABLE",
    )
    sch_off = TechnicianSchedule(
        technician_id=tech_off.id,
        work_date=target_date,
        start_time=time(8, 0),
        end_time=time(17, 0),
        status="OFF",
    )
    sch_morning = TechnicianSchedule(
        technician_id=tech_morning_only.id,
        work_date=target_date,
        start_time=time(8, 0),
        end_time=time(12, 0),
        status="AVAILABLE",
    )
    db.add(sch1)
    db.add(sch2)
    db.add(sch_software)
    db.add(sch_off)
    db.add(sch_morning)

    # Tạo lịch hẹn chính (9:00 - 10:00 ngày target_date)
    appt = Appointment(
        appointment_number=f"APPT-{uuid.uuid4().hex[:8].upper()}",
        appointment_date=appt_datetime,
        status=AppointmentStatus.PENDING.value,
        device_id=device.id,
        customer_id=cust.id,
    )
    db.add(appt)
    db.commit()

    # Gán dịch vụ màn hình cho lịch hẹn
    appt_svc = AppointmentService(
        appointment_id=appt.id,
        service_id=svc_screen.id,
        price_at_booking=svc_screen.base_price,
        quantity=1,
    )
    db.add(appt_svc)
    db.commit()
    db.refresh(appt)

    return {
        "customer": cust,
        "device": device,
        "service": svc_screen,
        "tech1": tech1,
        "tech2": tech2,
        "tech_software": tech_software,
        "tech_inactive": tech_inactive,
        "tech_off": tech_off,
        "tech_morning_only": tech_morning_only,
        "appointment": appt,
        "target_date": target_date,
    }


# ==============================================================================
# TESTS CHO API PHÂN CÔNG KỸ THUẬT VIÊN (POST /api/appointments/{id}/assign-technician)
# ==============================================================================


def test_assign_technician_success(client: TestClient, db: Session) -> None:
    """Test phân công thành công kỹ thuật viên đủ điều kiện cho lịch hẹn."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)

    res = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech1.id), "note": "Giao xử lý máy cho khách VIP"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["appointment_id"] == str(appt.id)
    assert data["data"]["technician_id"] == str(tech1.id)
    assert data["data"]["technician_name"] == tech1.full_name
    assert data["data"]["note"] == "Giao xử lý máy cho khách VIP"

    # Kiểm tra database đã cập nhật technician_id
    db.refresh(appt)
    assert appt.technician_id == tech1.id

    # Kiểm tra bản ghi lịch sử trạng thái
    histories = db.exec(
        select(RepairStatusHistory).where(RepairStatusHistory.appointment_id == appt.id)
    ).all()
    assert len(histories) >= 1
    last_h = histories[-1]
    assert tech1.full_name in last_h.note
    assert "Giao xử lý máy cho khách VIP" in last_h.note
    assert last_h.changed_by_user_id == staff.id


def test_assign_technician_reassign_different_tech_success(
    client: TestClient, db: Session
) -> None:
    """Test thay đổi kỹ thuật viên khi lịch hẹn đã có người phụ trách."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
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

    # Chuyển sang tech2 (cũng có chuyên môn liên quan bo mạch/máy)
    res = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech2.id), "note": "Đổi sang thợ tech2"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["technician_id"] == str(tech2.id)

    db.refresh(appt)
    assert appt.technician_id == tech2.id

    # Kiểm tra note lịch sử ghi rõ việc đổi từ tech1 sang tech2
    histories = db.exec(
        select(RepairStatusHistory).where(RepairStatusHistory.appointment_id == appt.id)
    ).all()
    last_h = histories[-1]
    assert f"từ {tech1.full_name} sang {tech2.full_name}" in last_h.note


def test_assign_technician_already_assigned_same_tech(
    client: TestClient, db: Session
) -> None:
    """Chặn phân công lại chính kỹ thuật viên đã phụ trách lịch hẹn (400 Bad Request)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)

    # Đã gán tech1
    appt.technician_id = tech1.id
    db.add(appt)
    db.commit()

    res = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech1.id)},
    )
    assert res.status_code == 400
    assert "đã được phân công cho lịch hẹn này từ trước" in res.json()["detail"]


def test_assign_technician_appointment_not_found(
    client: TestClient, db: Session
) -> None:
    """Kiểm tra 404 khi ID lịch hẹn không tồn tại."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    tech1 = fix["tech1"]
    assert isinstance(tech1, Technician)
    fake_id = uuid.uuid4()

    res = client.post(
        f"/api/v1/appointments/{fake_id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech1.id)},
    )
    assert res.status_code == 404
    assert "Không tìm thấy lịch hẹn" in res.json()["detail"]


def test_assign_technician_technician_not_found(
    client: TestClient, db: Session
) -> None:
    """Kiểm tra 404 khi ID kỹ thuật viên không tồn tại."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)
    fake_tech_id = uuid.uuid4()

    res = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(fake_tech_id)},
    )
    assert res.status_code == 404
    assert "Không tìm thấy kỹ thuật viên" in res.json()["detail"]


def test_assign_technician_inactive_technician(client: TestClient, db: Session) -> None:
    """Chặn phân công kỹ thuật viên đã nghỉ việc (is_active=False -> 400 Bad Request)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    tech_inactive = fix["tech_inactive"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech_inactive, Technician)

    res = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech_inactive.id)},
    )
    assert res.status_code == 400
    assert "không hoạt động hoặc đã nghỉ việc" in res.json()["detail"]


def test_assign_technician_on_leave_off(client: TestClient, db: Session) -> None:
    """Chặn phân công kỹ thuật viên có lịch nghỉ phép (status=OFF) trong ngày hẹn (400 Bad Request)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    tech_off = fix["tech_off"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech_off, Technician)

    res = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech_off.id)},
    )
    assert res.status_code == 400
    assert "đã đăng ký nghỉ (OFF)" in res.json()["detail"]


def test_assign_technician_out_of_shift(client: TestClient, db: Session) -> None:
    """Chặn phân công kỹ thuật viên không có ca làm việc bao quát khung giờ hẹn (400 Bad Request)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    target_date = fix["target_date"]
    tech_morning_only = fix["tech_morning_only"]
    assert isinstance(tech_morning_only, Technician)
    assert isinstance(target_date, date)

    # Tạo lịch hẹn buổi chiều lúc 14:00 (vượt quá ca sáng 08:00 - 12:00)
    afternoon_appt = Appointment(
        appointment_number=f"APPT-{uuid.uuid4().hex[:8].upper()}",
        appointment_date=datetime.combine(target_date, time(14, 0), tzinfo=UTC),
        status=AppointmentStatus.PENDING.value,
        device_id=fix["device"].id,  # type: ignore
        customer_id=fix["customer"].id,  # type: ignore
    )
    db.add(afternoon_appt)
    db.commit()

    res = client.post(
        f"/api/v1/appointments/{afternoon_appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech_morning_only.id)},
    )
    assert res.status_code == 400
    assert "không có ca làm việc phù hợp" in res.json()["detail"]


def test_assign_technician_specialization_mismatch(
    client: TestClient, db: Session
) -> None:
    """Chặn phân công kỹ thuật viên không có chuyên môn phù hợp với dịch vụ (400 Bad Request)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    tech_software = fix["tech_software"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech_software, Technician)

    # tech_software chuyên về phần mềm, trong khi lịch hẹn yêu cầu thay màn hình phần cứng
    res = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech_software.id)},
    )
    assert res.status_code == 400
    assert "không đủ điều kiện chuyên môn" in res.json()["detail"]


def test_assign_technician_schedule_conflict_overlap(
    client: TestClient, db: Session
) -> None:
    """Chặn phân công khi kỹ thuật viên bị trùng lịch hẹn khác trong khung giờ (409 Conflict)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    target_date = fix["target_date"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)
    assert isinstance(target_date, date)

    # Tạo một lịch hẹn khác của tech1 lúc 09:30 (trùng với khung giờ 09:00 - 10:00 của appt)
    conflict_appt = Appointment(
        appointment_number=f"APPT-CONFLICT-{uuid.uuid4().hex[:6].upper()}",
        appointment_date=datetime.combine(target_date, time(9, 30), tzinfo=UTC),
        status=AppointmentStatus.CONFIRMED.value,
        technician_id=tech1.id,
        device_id=fix["device"].id,  # type: ignore
        customer_id=fix["customer"].id,  # type: ignore
    )
    db.add(conflict_appt)
    db.commit()

    # Cố gắng gán tech1 cho appt lúc 09:00 - 10:00
    res = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech1.id)},
    )
    assert res.status_code == 409
    assert "đã bị trùng lịch với lịch hẹn khác" in res.json()["detail"]


def test_assign_technician_finished_appointment_conflict(
    client: TestClient, db: Session
) -> None:
    """Chặn phân công kỹ thuật viên cho lịch hẹn đã kết thúc (COMPLETED hoặc CANCELLED -> 409 Conflict)."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)

    appt.status = AppointmentStatus.COMPLETED.value
    db.add(appt)
    db.commit()

    res = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech1.id)},
    )
    assert res.status_code == 409
    assert "đã kết thúc" in res.json()["detail"]


def test_assign_technician_validation_bad_payload(
    client: TestClient, db: Session
) -> None:
    """Kiểm tra Pydantic validation (422) khi payload thiếu hoặc sai kiểu dữ liệu."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    assert isinstance(appt, Appointment)

    # Thiếu technician_id
    res1 = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={},
    )
    assert res1.status_code == 422

    # technician_id không phải UUID hợp lệ
    res2 = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": "NOT-A-UUID"},
    )
    assert res2.status_code == 422


def test_assign_technician_permissions_rbac(client: TestClient, db: Session) -> None:
    """Kiểm tra phân quyền: Customer bị từ chối 403 Forbidden, không token bị 401 Unauthorized."""
    cust_user = create_role_user(db, "customer")
    cust_headers = get_token_headers(cust_user)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)

    # 1. Customer gọi
    res1 = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=cust_headers,
        json={"technician_id": str(tech1.id)},
    )
    assert res1.status_code == 403

    # 2. Không token
    res2 = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        json={"technician_id": str(tech1.id)},
    )
    assert res2.status_code == 401


def test_assign_technician_transaction_rollback_on_error(
    monkeypatch, client: TestClient, db: Session
) -> None:
    """Kiểm tra tính nguyên tử của transaction: Lỗi cơ sở dữ liệu sẽ rollback hoàn toàn."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)

    original_commit = Session.commit

    def failing_commit(_self: Session) -> None:
        raise RuntimeError("Database connection interrupted during assign commit")

    monkeypatch.setattr(Session, "commit", failing_commit)

    res = client.post(
        f"/api/v1/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech1.id), "note": "Thử nghiệm lỗi rollback"},
    )
    assert res.status_code == 500
    assert (
        "Đã xảy ra lỗi trong quá trình phân công kỹ thuật viên" in res.json()["detail"]
    )

    # Khôi phục commit và kiểm tra database không bị lưu dở dang
    monkeypatch.setattr(Session, "commit", original_commit)
    db.expire_all()
    fresh_appt = db.get(Appointment, appt.id)
    assert fresh_appt is not None
    assert fresh_appt.technician_id is None


def test_assign_technician_alias_endpoint(client: TestClient, db: Session) -> None:
    """Kiểm tra gọi qua endpoint đề xuất POST /api/appointments/{id}/assign-technician hoạt động chuẩn xác."""
    staff = create_role_user(db, "staff")
    headers = get_token_headers(staff)
    fix = setup_appointment_assign_fixture(db)
    appt = fix["appointment"]
    tech1 = fix["tech1"]
    assert isinstance(appt, Appointment)
    assert isinstance(tech1, Technician)

    res = client.post(
        f"/api/appointments/{appt.id}/assign-technician",
        headers=headers,
        json={"technician_id": str(tech1.id), "note": "Test alias endpoint"},
    )
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["data"]["technician_id"] == str(tech1.id)
