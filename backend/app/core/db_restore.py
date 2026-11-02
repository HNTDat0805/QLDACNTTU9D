"""Database Backup & Restore utility module for FixPhone project.

Provides robust functions to:
- Export database state into a structured, verifiable backup file.
- Restore database state from a backup file with integrity verification.
- Enforce transaction atomicity and proper foreign key order.
- Validate backup file integrity (detecting corruption, missing metadata).
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, text
from sqlmodel import Session, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    AppointmentService,
    Customer,
    Device,
    Invoice,
    Notification,
    Payment,
    Quote,
    QuoteItem,
    RepairStatusHistory,
    Review,
    Service,
    Technician,
    TechnicianSchedule,
    User,
)

logger = get_logger("app.core.db_restore")

# Dependency order for table deletion (children first)
TABLE_MODELS_DELETION_ORDER = [
    Review,
    Notification,
    Payment,
    Invoice,
    QuoteItem,
    Quote,
    RepairStatusHistory,
    AppointmentService,
    Appointment,
    TechnicianSchedule,
    Device,
    Service,
    Technician,
    Customer,
    User,
]

# Dependency order for table restoration (parents first)
TABLE_MODELS_RESTORATION_ORDER = [
    User,
    Customer,
    Technician,
    Service,
    Device,
    TechnicianSchedule,
    Appointment,
    AppointmentService,
    RepairStatusHistory,
    Quote,
    QuoteItem,
    Invoice,
    Payment,
    Notification,
    Review,
]


class DatabaseRestoreError(Exception):
    """Lỗi chung trong quá trình khôi phục cơ sở dữ liệu."""

    pass


class CorruptedBackupError(DatabaseRestoreError):
    """Lỗi file backup bị hỏng, sai định dạng hoặc sai mã băm kiểm tra (checksum)."""

    pass


class TargetDatabaseError(DatabaseRestoreError):
    """Lỗi kết nối hoặc cơ sở dữ liệu đích không hợp lệ."""

    pass


def _calculate_checksum(data_str: str) -> str:
    """Tính toán mã băm SHA-256 để xác thực tính toàn vẹn của dữ liệu backup."""
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


def export_database_backup(session: Session, file_path: str | Path) -> dict[str, Any]:
    """Xuất toàn bộ dữ liệu database hiện tại thành file backup có checksum."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    backup_data: dict[str, list[dict[str, Any]]] = {}
    table_counts: dict[str, int] = {}

    for model in TABLE_MODELS_RESTORATION_ORDER:
        table_name = getattr(model, "__tablename__", model.__name__.lower())
        rows = session.exec(select(model)).all()
        table_counts[table_name] = len(rows)

        serialized_rows = []
        for row in rows:
            row_dict = row.model_dump()
            # Convert non-serializable objects (UUID, datetime, date, time) to str
            for k, v in row_dict.items():
                if isinstance(v, uuid.UUID):
                    row_dict[k] = str(v)
                elif isinstance(v, datetime):
                    row_dict[k] = v.isoformat()
            serialized_rows.append(row_dict)

        backup_data[table_name] = serialized_rows

    data_payload_json = json.dumps(backup_data, ensure_ascii=False, sort_keys=True)
    checksum = _calculate_checksum(data_payload_json)

    full_backup_envelope = {
        "version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "database_system": "PostgreSQL / SQLAlchemy SQLModel",
        "checksum_sha256": checksum,
        "table_counts": table_counts,
        "data": backup_data,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(full_backup_envelope, f, ensure_ascii=False, indent=2)

    logger.info(
        f"Đã xuất bản backup database thành công: {file_path} (tổng {sum(table_counts.values())} bản ghi)"
    )
    return full_backup_envelope


def restore_database_from_backup(
    session: Session,
    file_path: str | Path,
    clean_existing: bool = True,
) -> dict[str, int]:
    """Khôi phục dữ liệu database từ file backup.

    Quy trình:
    1. Kiểm tra sự tồn tại của file backup.
    2. Đọc và kiểm tra cấu trúc JSON, tính toàn vẹn (checksum).
    3. Kiểm tra kết nối tới cơ sở dữ liệu đích.
    4. Xóa dữ liệu cũ theo đúng thứ tự khóa ngoại nếu clean_existing=True.
    5. Nạp dữ liệu các bảng theo đúng thứ tự phụ thuộc cha-con.
    6. Commit transaction hoặc Rollback nếu có lỗi phát sinh.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file backup tại đường dẫn: {path}")

    # 1. Đọc nội dung file backup
    try:
        with open(path, encoding="utf-8") as f:
            envelope = json.load(f)
    except json.JSONDecodeError as exc:
        raise CorruptedBackupError(
            f"File backup bị hỏng hoặc không đúng định dạng JSON: {exc}"
        ) from exc

    # 2. Kiểm tra tính toàn vẹn (Envelope & Checksum)
    if (
        not isinstance(envelope, dict)
        or "data" not in envelope
        or "checksum_sha256" not in envelope
    ):
        raise CorruptedBackupError(
            "File backup thiếu trường bắt buộc 'data' hoặc 'checksum_sha256'"
        )

    expected_checksum = envelope["checksum_sha256"]
    data_payload_str = json.dumps(envelope["data"], ensure_ascii=False, sort_keys=True)
    actual_checksum = _calculate_checksum(data_payload_str)

    if expected_checksum != actual_checksum:
        raise CorruptedBackupError(
            f"Mã kiểm tra tính toàn vẹn (checksum) không khớp! Expected={expected_checksum}, Actual={actual_checksum}"
        )

    # 3. Kiểm tra kết nối database đích
    try:
        session.exec(text("SELECT 1"))
    except Exception as exc:
        raise TargetDatabaseError(
            f"Không thể kết nối hoặc database đích không khả dụng: {exc}"
        ) from exc

    restored_counts: dict[str, int] = {}

    try:
        # 4. Xóa dữ liệu hiện tại theo thứ tự con -> cha để không dính Foreign Key vi phạm
        if clean_existing:
            for model in TABLE_MODELS_DELETION_ORDER:
                session.exec(delete(model))
            session.flush()

        # 5. Phục hồi dữ liệu theo thứ tự cha -> con
        raw_data = envelope["data"]

        for model in TABLE_MODELS_RESTORATION_ORDER:
            table_name = getattr(model, "__tablename__", model.__name__.lower())
            table_rows = raw_data.get(table_name, [])

            count = 0
            for row_dict in table_rows:
                # Convert date/datetime/uuid string fields back to appropriate objects
                clean_row = {}
                for k, v in row_dict.items():
                    if v is None:
                        clean_row[k] = None
                    elif isinstance(v, str):
                        # Attempt UUID parse
                        if k.endswith("_id") or k == "id":
                            try:
                                clean_row[k] = uuid.UUID(v)
                            except ValueError:
                                clean_row[k] = v
                        # Attempt ISO datetime parse
                        elif (
                            k.endswith("_at")
                            or k.endswith("_date")
                            or k in ("valid_until",)
                        ):
                            try:
                                clean_row[k] = datetime.fromisoformat(v)
                            except ValueError:
                                clean_row[k] = v
                        else:
                            clean_row[k] = v
                    else:
                        clean_row[k] = v

                db_instance = model(**clean_row)
                session.add(db_instance)
                count += 1

            session.flush()
            restored_counts[table_name] = count

        session.commit()
        logger.info(
            f"Khôi phục cơ sở dữ liệu thành công từ {path}. Tổng số bản ghi: {sum(restored_counts.values())}"
        )
        return restored_counts

    except Exception as exc:
        session.rollback()
        logger.error(f"Lỗi trong quá trình khôi phục database: {exc}", exc_info=True)
        raise DatabaseRestoreError(
            f"Khôi phục database thất bại và đã rollback an toàn: {exc}"
        ) from exc
