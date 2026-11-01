"""Read-only local demo prerequisites. Never prints credentials or personal data."""

import json
import logging
import os
import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root / "backend")
    sys.path.insert(0, str(root / "backend"))
    warnings.filterwarnings("ignore", category=UserWarning)
    logging.disable(logging.CRITICAL)
    try:
        from app.core.config import settings
        from app.models import Service, Technician, TechnicianSchedule, User
        from sqlmodel import Session, col, create_engine, func, select

        engine = create_engine(
            str(settings.DATABASE_URL),
            connect_args={"connect_timeout": 5},
            hide_parameters=True,
        )
        with engine.connect() as connection, connection.begin():
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            read_only = connection.exec_driver_sql(
                "SHOW transaction_read_only"
            ).scalar()
            if read_only != "on":
                raise RuntimeError("Read-only transaction not established")
            with Session(bind=connection) as session:
                accounts = {
                    role: session.exec(
                        select(func.count())
                        .select_from(User)
                        .where(
                            User.role == role,
                            col(User.is_active).is_(True),
                            col(User.is_superuser).is_(False),
                        )
                    ).one()
                    for role in ("customer", "staff", "technician", "manager")
                }
                services = session.exec(
                    select(func.count())
                    .select_from(Service)
                    .where(
                        col(Service.is_active).is_(True),
                        Service.estimated_duration_minutes > 0,
                    )
                ).one()
                linked = (
                    select(Technician.id)
                    .join(User)
                    .where(
                        col(Technician.is_active).is_(True),
                        User.role == "technician",
                        col(User.is_active).is_(True),
                        col(User.is_superuser).is_(False),
                    )
                )
                linked_ids = list(session.exec(linked).all())
                schedules = session.exec(
                    select(func.count())
                    .select_from(TechnicianSchedule)
                    .where(
                        col(TechnicianSchedule.technician_id).in_(linked_ids),
                        TechnicianSchedule.work_date
                        >= datetime.now(UTC).astimezone().date(),
                        TechnicianSchedule.status == "AVAILABLE",
                        TechnicianSchedule.end_time > TechnicianSchedule.start_time,
                    )
                ).one()
                mismatch = session.exec(
                    select(func.count())
                    .select_from(User)
                    .where(
                        User.role == "customer",
                        col(User.is_superuser).is_(True),
                    )
                ).one()
                report = {
                    "database": "CONNECTED",
                    "transaction_read_only": True,
                    "active_services_with_duration": services,
                    "active_non_superuser_accounts": accounts,
                    "active_linked_technicians": len(linked_ids),
                    "available_shifts_today_or_future": schedules,
                    "customer_role_with_superuser_flag": mismatch,
                    "data_prerequisites_ready": bool(
                        services and all(accounts.values()) and linked_ids and schedules
                    ),
                }
        engine.dispose()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (SQLAlchemyError, ValueError, RuntimeError, OSError, ImportError) as error:
        # Exception messages can contain database URLs or configuration values.
        print(
            json.dumps({"database": "CHECK_FAILED", "error_type": type(error).__name__})
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
