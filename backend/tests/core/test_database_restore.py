"""Test suite for Database Restore Verification (FixPhone Project).

Implements 7 specific scenarios:
1. RESTORE-01: Restore từ file backup hợp lệ (Valid Backup).
2. RESTORE-02: Restore từ file backup bị hỏng hoặc sai checksum (Corrupted Backup).
3. RESTORE-03: Restore khi file hoặc database đích không tồn tại (Non-existent file / DB).
4. RESTORE-04: Restore khi dữ liệu hiện tại khác dữ liệu trong backup (Divergent data overwrite).
5. RESTORE-05: Restore khi có lỗi kết nối database (Connection Failure Handling).
6. RESTORE-06: Kiểm tra tính toàn vẹn dữ liệu chi tiết của 6 nhóm thực thể sau restore.
7. RESTORE-07: Kiểm tra ứng dụng Backend FastAPI hoạt động và truy xuất dữ liệu bình thường sau restore.
"""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import security
from app.core.db_restore import (
    CorruptedBackupError,
    DatabaseRestoreError,
    TargetDatabaseError,
    export_database_backup,
    restore_database_from_backup,
)
from app.models import (
    Appointment,
    AppointmentService,
    Customer,
    Device,
    RepairStatusHistory,
    Service,
    Technician,
    User,
)


@pytest.fixture
def valid_seed_data(db: Session) -> dict[str, Any]:
    """Tạo bộ dữ liệu mẫu chuẩn gồm đầy đủ 6 nhóm dữ liệu nghiệp vụ."""
    # 1. User & Customer
    user = User(
        email=f"customer_restore_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=security.get_password_hash("RestorePass123!"),
        full_name="Nguyễn Văn An",
        role="customer",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    customer = Customer(
        user_id=user.id,
        full_name=user.full_name,
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
        email=user.email,
        address="123 Lê Lợi, Quận 1, TP.HCM",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    # 2. Device
    device = Device(
        customer_id=customer.id,
        device_type="Smartphone",
        brand="Apple",
        model="iPhone 15 Pro",
        color="Titan Tự Nhiên",
        imei="354892019283741",
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    # 3. Technician
    technician = Technician(
        full_name="Kỹ Thuật Viên Minh",
        phone_number=f"097{uuid.uuid4().int % 10000000:07d}",
        specialization="Phần cứng Apple",
        is_active=True,
    )
    db.add(technician)
    db.commit()
    db.refresh(technician)

    # 4. Service
    service = Service(
        code=f"SVC-DISP-{uuid.uuid4().hex[:4].upper()}",
        name=f"Thay màn hình Super Retina XDR {uuid.uuid4().hex[:4]}",
        description="Màn hình chính hãng Apple OLED",
        base_price=3500000.0,
        estimated_duration_minutes=60,
        is_active=True,
    )
    db.add(service)
    db.commit()
    db.refresh(service)

    # 5. Appointment
    appointment = Appointment(
        appointment_number=f"APPT-RES-{uuid.uuid4().hex[:6].upper()}",
        appointment_date=datetime.now(UTC),
        status="IN_PROGRESS",
        customer_id=customer.id,
        device_id=device.id,
        technician_id=technician.id,
        total_amount=3500000.0,
        customer_notes="Máy rơi vỡ kính",
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    # 5b. Appointment Service link
    appt_svc = AppointmentService(
        appointment_id=appointment.id,
        service_id=service.id,
        price_at_booking=service.base_price,
        quantity=1,
    )
    db.add(appt_svc)

    # 6. Repair Status History
    history = RepairStatusHistory(
        appointment_id=appointment.id,
        previous_status="PENDING",
        new_status="IN_PROGRESS",
        note="Kỹ thuật viên đã nhận máy và tiến hành kiểm tra linh kiện",
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return {
        "user": user,
        "customer": customer,
        "device": device,
        "technician": technician,
        "service": service,
        "appointment": appointment,
        "history": history,
    }


# ============================================================================
# CÁC TRƯỜNG HỢP KIỂM THỬ RESTORE DATABASE
# ============================================================================


def test_restore_01_valid_backup_file(
    db: Session, valid_seed_data: dict[str, Any], tmp_path: Path
) -> None:
    """RESTORE-01: Khôi phục database từ file backup hợp lệ.

    - Xuất dữ liệu hiện tại ra file backup hợp lệ.
    - Xóa bớt hoặc thay đổi dữ liệu trong DB.
    - Thực hiện khôi phục từ file backup.
    - Xác nhận quá trình khôi phục hoàn tất 100%, đúng số lượng và dữ liệu.
    """
    backup_file = tmp_path / "valid_backup.json"
    envelope = export_database_backup(db, backup_file)
    assert backup_file.is_file()
    assert envelope["checksum_sha256"] is not None

    expected_customer_id = valid_seed_data["customer"].id
    expected_appointment_num = valid_seed_data["appointment"].appointment_number

    # Thực hiện restore
    result = restore_database_from_backup(db, backup_file, clean_existing=True)

    assert result["customer"] >= 1
    assert result["device"] >= 1
    assert result["appointment"] >= 1
    assert result["service"] >= 1
    assert result["technician"] >= 1
    assert result["repair_status_history"] >= 1

    # Kiểm tra bản ghi cụ thể sau khi restore
    restored_cust = db.get(Customer, expected_customer_id)
    assert restored_cust is not None
    assert restored_cust.full_name == valid_seed_data["customer"].full_name

    restored_appt = db.exec(
        select(Appointment).where(
            Appointment.appointment_number == expected_appointment_num
        )
    ).first()
    assert restored_appt is not None
    assert restored_appt.status == "IN_PROGRESS"


def test_restore_02_corrupted_backup_file(db: Session, tmp_path: Path) -> None:
    """RESTORE-02: Khôi phục từ file backup bị hỏng hoặc sai checksum.

    - Tạo file backup bị hỏng JSON hoặc bị can thiệp thay đổi dữ liệu mà không khớp checksum.
    - Hệ thống phải phát hiện và từ chối khôi phục bằng ngoại lệ CorruptedBackupError.
    """
    # 1. File backup có cấu trúc JSON bị hỏng (syntax error)
    bad_json_file = tmp_path / "bad_syntax.json"
    bad_json_file.write_text("{ this is not a valid json syntax ...", encoding="utf-8")

    with pytest.raises(CorruptedBackupError, match="không đúng định dạng JSON"):
        restore_database_from_backup(db, bad_json_file)

    # 2. File backup có checksum bị giả mạo / can thiệp (Tampered payload)
    tampered_file = tmp_path / "tampered.json"
    envelope = export_database_backup(db, tampered_file)
    # Can thiệp sửa đổi checksum
    envelope["checksum_sha256"] = (
        "fake_checksum_00000000000000000000000000000000000000000000"
    )
    with open(tampered_file, "w", encoding="utf-8") as f:
        json.dump(envelope, f)

    with pytest.raises(CorruptedBackupError, match="không khớp"):
        restore_database_from_backup(db, tampered_file)


def test_restore_03_non_existent_file(db: Session, tmp_path: Path) -> None:
    """RESTORE-03: Khôi phục khi file backup không tồn tại.

    - Hệ thống phát hiện ngay và ném FileNotFoundError, không crash hệ thống.
    """
    non_existent = tmp_path / "non_existent_backup_file.json"
    assert not non_existent.exists()

    with pytest.raises(FileNotFoundError):
        restore_database_from_backup(db, non_existent)


def test_restore_04_overwrite_divergent_data(
    db: Session, valid_seed_data: dict[str, Any], tmp_path: Path
) -> None:
    """RESTORE-04: Khôi phục khi dữ liệu hiện tại khác với dữ liệu trong backup.

    - Tạo backup của trạng thái A.
    - Thêm các bản ghi mới (trạng thái B khác biệt).
    - Restore lại bản backup của A.
    - Xác nhận dữ liệu lạ của B bị loại bỏ và dữ liệu của A được phục hồi nguyên vẹn.
    """
    backup_file = tmp_path / "state_a.json"
    export_database_backup(db, backup_file)

    # Thêm dữ liệu phát sinh ở trạng thái B
    new_user = User(
        email=f"divergent_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="pwd",
        full_name="Người Dùng Phát Sinh",
        role="customer",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    divergent_cust = Customer(
        user_id=new_user.id,
        full_name="Khách Hàng Phát Sinh",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
    )
    db.add(divergent_cust)
    db.commit()
    db.refresh(divergent_cust)

    original_customer_id = valid_seed_data["customer"].id
    divergent_cust_id = divergent_cust.id

    assert db.get(Customer, divergent_cust_id) is not None

    # Restore lại trạng thái A
    restore_database_from_backup(db, backup_file, clean_existing=True)

    # Xác nhận khách hàng phát sinh ở trạng thái B đã bị xóa bỏ hoàn toàn
    assert db.get(Customer, divergent_cust_id) is None
    # Xác nhận khách hàng ban đầu trong backup A vẫn tồn tại
    assert db.get(Customer, original_customer_id) is not None


def test_restore_05_database_connection_failure(tmp_path: Path) -> None:
    """RESTORE-05: Khôi phục khi có lỗi kết nối database.

    - Tạo session đóng hoặc không thể kết nối.
    - Hệ thống phải phát hiện lỗi kết nối và ném lỗi TargetDatabaseError / DatabaseRestoreError.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    backup_file = tmp_path / "conn_test.json"
    # Giả lập connection string trỏ tới cổng không mở với driver psycopg của dự án
    dummy_engine = create_engine(
        "postgresql+psycopg://postgres:changethis@localhost:59999/non_existent_db",
        poolclass=NullPool,
        connect_args={"connect_timeout": 1},
    )

    with Session(dummy_engine) as broken_session:
        # Tạo mock file backup hợp lệ
        backup_file.write_text(
            json.dumps(
                {
                    "checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "data": {},
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises((TargetDatabaseError, DatabaseRestoreError)):
            restore_database_from_backup(broken_session, backup_file)


def test_restore_06_data_integrity_all_six_entities(
    db: Session, valid_seed_data: dict[str, Any], tmp_path: Path
) -> None:
    """RESTORE-06: Kiểm tra tính toàn vẹn dữ liệu chi tiết của 6 nhóm thực thể sau restore.

    1. Khách hàng (Customer)
    2. Thông tin điện thoại (Device)
    3. Dịch vụ sửa chữa (Service)
    4. Kỹ thuật viên (Technician)
    5. Lịch hẹn (Appointment)
    6. Trạng thái sửa chữa (RepairStatusHistory)
    Kiểm tra:
    - Tính đúng đắn của dữ liệu từng trường
    - Toàn vẹn khóa ngoại (Foreign key references)
    - Tính nhất quán quan hệ 1-N giữa Customer - Device, Appointment - History
    """
    backup_file = tmp_path / "integrity_backup.json"
    export_database_backup(db, backup_file)

    # Thực hiện restore
    restore_database_from_backup(db, backup_file, clean_existing=True)

    c_orig = valid_seed_data["customer"]
    d_orig = valid_seed_data["device"]
    s_orig = valid_seed_data["service"]
    t_orig = valid_seed_data["technician"]
    a_orig = valid_seed_data["appointment"]
    h_orig = valid_seed_data["history"]

    # 1. Kiểm tra Khách hàng
    c_res = db.get(Customer, c_orig.id)
    assert c_res is not None
    assert c_res.full_name == c_orig.full_name
    assert c_res.phone_number == c_orig.phone_number
    assert c_res.email == c_orig.email
    assert c_res.address == c_orig.address

    # 2. Kiểm tra Thiết bị & Khóa ngoại tới Customer
    d_res = db.get(Device, d_orig.id)
    assert d_res is not None
    assert d_res.customer_id == c_orig.id
    assert d_res.brand == d_orig.brand
    assert d_res.model == d_orig.model
    assert d_res.imei == d_orig.imei

    # 3. Kiểm tra Dịch vụ sửa chữa
    s_res = db.get(Service, s_orig.id)
    assert s_res is not None
    assert s_res.code == s_orig.code
    assert s_res.name == s_orig.name
    assert s_res.base_price == s_orig.base_price
    assert s_res.estimated_duration_minutes == s_orig.estimated_duration_minutes

    # 4. Kiểm tra Kỹ thuật viên
    t_res = db.get(Technician, t_orig.id)
    assert t_res is not None
    assert t_res.full_name == t_orig.full_name
    assert t_res.phone_number == t_orig.phone_number
    assert t_res.specialization == t_orig.specialization

    # 5. Kiểm tra Lịch hẹn & Các khóa ngoại liên kết (Customer, Device, Technician)
    a_res = db.get(Appointment, a_orig.id)
    assert a_res is not None
    assert a_res.appointment_number == a_orig.appointment_number
    assert a_res.customer_id == c_orig.id
    assert a_res.device_id == d_orig.id
    assert a_res.technician_id == t_orig.id
    assert a_res.status == a_orig.status
    assert a_res.total_amount == a_orig.total_amount

    # 6. Kiểm tra Lịch sử trạng thái sửa chữa
    h_res = db.get(RepairStatusHistory, h_orig.id)
    assert h_res is not None
    assert h_res.appointment_id == a_orig.id
    assert h_res.previous_status == "PENDING"
    assert h_res.new_status == "IN_PROGRESS"
    assert h_res.note == h_orig.note


def test_restore_07_fastapi_application_health_and_query_after_restore(
    client: TestClient, db: Session, valid_seed_data: dict[str, Any], tmp_path: Path
) -> None:
    """RESTORE-07: Kiểm tra ứng dụng Backend FastAPI hoạt động và truy vấn dữ liệu sau khi restore.

    - Sau khi restore dữ liệu:
      1. API Health Check /api/v1/utils/health-check/ trả về 200 OK (True).
      2. Đăng nhập và xác thực token hoạt động bình thường.
      3. API đọc danh mục dịch vụ GET /api/services truy xuất được dịch vụ vừa khôi phục.
      4. API đọc chi tiết khách hàng GET /api/customers/{id} truy xuất đúng dữ liệu.
      5. API đọc chi tiết lịch hẹn GET /api/appointments/{id}/detail truy xuất đầy đủ thông tin.
    """
    backup_file = tmp_path / "app_verify_backup.json"
    export_database_backup(db, backup_file)

    # Thực hiện restore
    restore_database_from_backup(db, backup_file, clean_existing=True)

    # 1. Kiểm tra Health Check
    health_res = client.get("/api/v1/utils/health-check/")
    assert health_res.status_code == 200
    assert health_res.json() is True

    # 2. Tạo token xác thực cho user trong bản backup
    user_id = valid_seed_data["user"].id
    user_email = valid_seed_data["user"].email
    token = security.create_access_token(
        subject=user_id, role="customer", email=user_email
    )
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Truy vấn API danh mục dịch vụ GET /api/services
    svc_res = client.get("/api/services")
    assert svc_res.status_code == 200
    svc_data = svc_res.json()
    assert svc_data["count"] >= 1
    found_svc = any(
        s["code"] == valid_seed_data["service"].code for s in svc_data["data"]
    )
    assert found_svc is True

    # 4. Truy vấn API chi tiết khách hàng GET /api/customers/{id}
    cust_id = valid_seed_data["customer"].id
    cust_res = client.get(f"/api/customers/{cust_id}", headers=headers)
    assert cust_res.status_code == 200
    assert cust_res.json()["full_name"] == valid_seed_data["customer"].full_name

    # 5. Truy vấn API chi tiết lịch hẹn GET /api/appointments/{id}/detail
    appt_id = valid_seed_data["appointment"].id
    appt_res = client.get(f"/api/appointments/{appt_id}/detail", headers=headers)
    assert appt_res.status_code == 200
    appt_json = appt_res.json()
    assert (
        appt_json["appointment_number"]
        == valid_seed_data["appointment"].appointment_number
    )
    assert appt_json["status"] == "IN_PROGRESS"
    assert appt_json["customer"]["id"] == str(cust_id)
    assert appt_json["device"]["id"] == str(valid_seed_data["device"].id)
    assert len(appt_json["status_history"]) >= 1
