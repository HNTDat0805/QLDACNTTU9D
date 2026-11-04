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
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

from sqlalchemy import Date, DateTime, Time, delete
from sqlmodel import Session, SQLModel, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    AppointmentService,
    Customer,
    Device,
    Invoice,
    InvoiceItem,
    Item,
    Notification,
    PasswordResetToken,
    Payment,
    Quote,
    QuoteItem,
    RefreshToken,
    RepairStatusHistory,
    Review,
    Service,
    SystemLog,
    Technician,
    TechnicianSchedule,
    User,
)

logger = get_logger("app.core.db_restore")

# Dependency order for table deletion (children first)
TABLE_MODELS_DELETION_ORDER: list[type[SQLModel]] = [
    Review,
    Notification,
    Payment,
    InvoiceItem,
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
    RefreshToken,
    PasswordResetToken,
    Item,
    SystemLog,
    User,
]

# Dependency order for table restoration (parents first)
TABLE_MODELS_RESTORATION_ORDER: list[type[SQLModel]] = [
    User,
    SystemLog,
    Item,
    RefreshToken,
    PasswordResetToken,
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
    InvoiceItem,
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


def _deserialize_column_value(model: type[SQLModel], key: str, value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value

    sa_table = getattr(model, "__table__", None)
    if sa_table is not None and key in sa_table.columns:
        col_type = sa_table.columns[key].type
        try:
            if col_type.python_type is uuid.UUID:
                return uuid.UUID(value)
        except NotImplementedError, ValueError:
            pass
        if isinstance(col_type, DateTime):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return value
        if isinstance(col_type, Date) and not isinstance(col_type, DateTime):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return value
        if isinstance(col_type, Time):
            try:
                return time.fromisoformat(value)
            except ValueError:
                return value

    if key == "id" or key.endswith("_id"):
        try:
            return uuid.UUID(value)
        except ValueError:
            return value
    if key.endswith("_at") or key in ("valid_until", "appointment_date"):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
    if key.endswith("_date"):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value
    if key.endswith("_time"):
        try:
            return time.fromisoformat(value)
        except ValueError:
            return value
    return value


def export_database_backup(session: Session, file_path: str | Path) -> dict[str, Any]:
    """Xuất toàn bộ dữ liệu database hiện tại thành file backup có checksum."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    backup_data: dict[str, list[dict[str, Any]]] = {}
    table_counts: dict[str, int] = {}

    for model in TABLE_MODELS_RESTORATION_ORDER:
        table_name = str(getattr(model, "__tablename__", model.__name__.lower()))
        rows: list[SQLModel] = list(session.exec(select(model)).all())
        table_counts[table_name] = len(rows)

        serialized_rows: list[dict[str, Any]] = []
        for row in rows:
            row_dict = row.model_dump()
            for k, v in row_dict.items():
                if isinstance(v, uuid.UUID):
                    row_dict[k] = str(v)
                elif isinstance(v, datetime | date | time):
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
    """Khôi phục dữ liệu database từ file backup."""
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
        session.exec(select(1)).one()
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
            table_name = str(getattr(model, "__tablename__", model.__name__.lower()))
            table_rows = raw_data.get(table_name, [])

            count = 0
            for row_dict in table_rows:
                clean_row: dict[str, Any] = {
                    k: _deserialize_column_value(model, k, v)
                    for k, v in row_dict.items()
                }
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
