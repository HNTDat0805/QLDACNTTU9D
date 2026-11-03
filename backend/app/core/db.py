from datetime import date, time, timedelta

from sqlalchemy import or_
from sqlmodel import Session, col, create_engine, select

from app import crud
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import (
    Appointment,
    Customer,
    Technician,
    TechnicianSchedule,
    User,
    UserCreate,
    UserRole,
)

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def _get_initial_role_users() -> list[tuple[str, str, str, UserRole, bool]]:
    default_pwd = settings.FIRST_SUPERUSER_PASSWORD
    return [
        (
            str(settings.FIRST_MANAGER),
            settings.FIRST_MANAGER_PASSWORD or default_pwd,
            "Quản lý cửa hàng",
            UserRole.MANAGER,
            False,
        ),
        (
            str(settings.FIRST_STAFF),
            settings.FIRST_STAFF_PASSWORD or default_pwd,
            "Nhân viên tiếp nhận",
            UserRole.STAFF,
            False,
        ),
        (
            str(settings.FIRST_TECHNICIAN),
            settings.FIRST_TECHNICIAN_PASSWORD or default_pwd,
            "Kỹ thuật viên sửa chữa",
            UserRole.TECHNICIAN,
            False,
        ),
        (
            str(settings.FIRST_CUSTOMER),
            settings.FIRST_CUSTOMER_PASSWORD or default_pwd,
            "Khách hàng mẫu",
            UserRole.CUSTOMER,
            False,
        ),
    ]


def _ensure_user(
    session: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
    is_superuser: bool = False,
) -> User:
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        user_in = UserCreate(
            email=email,
            password=password,
            full_name=full_name,
            role=role.value,
            is_superuser=is_superuser,
            is_active=True,
        )
        return crud.create_user(session=session, user_create=user_in)

    updated = False
    if user.role != role.value:
        user.role = role.value
        updated = True
    if is_superuser and not user.is_superuser:
        user.is_superuser = True
        updated = True
    if not user.is_active:
        user.is_active = True
        updated = True
    verified, updated_hash = verify_password(password, user.hashed_password)
    if not verified:
        user.hashed_password = get_password_hash(password)
        updated = True
    elif updated_hash:
        user.hashed_password = updated_hash
        updated = True
    if not user.full_name:
        user.full_name = full_name
        updated = True
    if updated:
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    _ensure_user(
        session,
        email=str(settings.FIRST_SUPERUSER),
        password=settings.FIRST_SUPERUSER_PASSWORD,
        full_name="Quản trị viên hệ thống",
        role=UserRole.ADMIN,
        is_superuser=True,
    )

    for email, password, full_name, role, is_superuser in _get_initial_role_users():
        user = _ensure_user(
            session,
            email=email,
            password=password,
            full_name=full_name,
            role=role,
            is_superuser=is_superuser,
        )
        if role == UserRole.TECHNICIAN:
            default_tech_phone = "0901000001"
            technician = session.exec(
                select(Technician).where(
                    or_(
                        col(Technician.user_id) == user.id,
                        col(Technician.phone_number) == default_tech_phone,
                    )
                )
            ).first()
            if not technician:
                session.add(
                    Technician(
                        full_name=full_name,
                        phone_number=default_tech_phone,
                        specialization="Sửa chữa phần cứng & màn hình",
                        is_active=True,
                        user_id=user.id,
                    )
                )
                session.commit()
            elif technician.user_id != user.id:
                technician.user_id = user.id
                session.add(technician)
                session.commit()
        elif role == UserRole.CUSTOMER:
            default_cust_phone = "0902000001"
            customer = session.exec(
                select(Customer).where(
                    or_(
                        col(Customer.user_id) == user.id,
                        col(Customer.phone_number) == default_cust_phone,
                    )
                )
            ).first()
            if not customer:
                session.add(
                    Customer(
                        full_name=full_name,
                        phone_number=default_cust_phone,
                        email=user.email,
                        address="TP. Hồ Chí Minh",
                        user_id=user.id,
                    )
                )
                session.commit()
            elif customer.user_id != user.id:
                customer.user_id = user.id
                session.add(customer)
                session.commit()

    # Seed technician working schedules for active technicians (next 60 days)
    active_techs = session.exec(
        select(Technician).where(col(Technician.is_active).is_(True))
    ).all()
    today = date.today()
    for tech in active_techs:
        for offset in range(-7, 60):
            target_date = today + timedelta(days=offset)
            existing = session.exec(
                select(TechnicianSchedule)
                .where(TechnicianSchedule.technician_id == tech.id)
                .where(TechnicianSchedule.work_date == target_date)
            ).first()
            if not existing:
                session.add(
                    TechnicianSchedule(
                        technician_id=tech.id,
                        work_date=target_date,
                        start_time=time(8, 0),
                        end_time=time(18, 0),
                        status="AVAILABLE",
                    )
                )
        session.commit()

    # Đảm bảo tất cả các lịch hẹn hiện có đều có báo giá (Quote)
    from app.services.quote_service import ensure_quote_for_appointment

    all_appointments = session.exec(select(Appointment)).all()
    for appt in all_appointments:
        ensure_quote_for_appointment(session, appt)
    session.commit()

    # Đảm bảo tất cả các đơn sửa chữa hoàn thành (COMPLETED) đều có hóa đơn (Invoice)
    from app.services.commerce_service import ensure_invoice_for_appointment

    completed_appointments = session.exec(
        select(Appointment).where(Appointment.status == "COMPLETED")
    ).all()
    for appt in completed_appointments:
        ensure_invoice_for_appointment(session, appt)
    session.commit()
