import uuid
from datetime import UTC, date, datetime, time

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlmodel import Session, col, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    AppointmentHistoryDetail,
    AppointmentService,
    AppointmentServiceItemDetail,
    AppointmentsHistoryPublic,
    Customer,
    CustomerPublic,
    Device,
    DevicePublic,
    RepairStatusHistory,
    RepairStatusHistoryPublic,
    Service,
    Technician,
    TechnicianPublic,
    User,
)

logger = get_logger("app.services.history_service")


def build_appointment_history_detail(
    session: Session,
    appointment: Appointment,
) -> AppointmentHistoryDetail:
    """Xây dựng dữ liệu chi tiết toàn diện của một lịch hẹn bao gồm tất cả các quan hệ và lịch sử."""
    customer = session.get(Customer, appointment.customer_id)
    device = session.get(Device, appointment.device_id)
    tech = (
        session.get(Technician, appointment.technician_id)
        if appointment.technician_id
        else None
    )

    # Lấy danh sách dịch vụ kèm giá tại thời điểm đặt (price_at_booking)
    svc_records = session.exec(
        select(AppointmentService, Service)
        .join(Service, col(AppointmentService.service_id) == col(Service.id))
        .where(AppointmentService.appointment_id == appointment.id)
    ).all()

    service_items = [
        AppointmentServiceItemDetail(
            service_id=svc.id,
            service_name=svc.name,
            price_at_booking=appt_svc.price_at_booking,
            quantity=appt_svc.quantity,
            notes=appt_svc.notes,
        )
        for appt_svc, svc in svc_records
    ]

    # Lấy dòng thời gian lịch sử trạng thái từ RepairStatusHistory
    history_records = session.exec(
        select(RepairStatusHistory)
        .where(RepairStatusHistory.appointment_id == appointment.id)
        .order_by(col(RepairStatusHistory.created_at).asc())
    ).all()

    status_histories = [
        RepairStatusHistoryPublic.model_validate(h) for h in history_records
    ]

    return AppointmentHistoryDetail(
        id=appointment.id,
        appointment_number=appointment.appointment_number,
        appointment_date=appointment.appointment_date,
        status=appointment.status,
        cancellation_reason=appointment.cancellation_reason,
        customer_notes=appointment.customer_notes,
        technician_diagnosis=appointment.technician_diagnosis,
        estimated_completion_date=appointment.estimated_completion_date,
        actual_completion_date=appointment.actual_completion_date,
        total_amount=appointment.total_amount,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
        customer=CustomerPublic.model_validate(customer) if customer else None,
        device=DevicePublic.model_validate(device) if device else None,
        technician=TechnicianPublic.model_validate(tech) if tech else None,
        services=service_items,
        status_history=status_histories,
    )


def get_appointment_history_list(
    session: Session,
    skip: int = 0,
    limit: int = 20,
    customer_id: uuid.UUID | None = None,
    technician_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    q: str | None = None,
) -> AppointmentsHistoryPublic:
    """Tra cứu và lọc lịch sử lịch hẹn sửa chữa trên toàn hệ thống."""
    query = select(Appointment)
    count_query = select(func.count()).select_from(Appointment)

    if customer_id:
        query = query.where(Appointment.customer_id == customer_id)
        count_query = count_query.where(Appointment.customer_id == customer_id)

    if technician_id:
        query = query.where(Appointment.technician_id == technician_id)
        count_query = count_query.where(Appointment.technician_id == technician_id)

    if status_filter and status_filter.strip():
        statuses = [s.strip().upper() for s in status_filter.split(",") if s.strip()]
        if len(statuses) == 1:
            query = query.where(Appointment.status == statuses[0])
            count_query = count_query.where(Appointment.status == statuses[0])
        elif len(statuses) > 1:
            query = query.where(col(Appointment.status).in_(statuses))
            count_query = count_query.where(col(Appointment.status).in_(statuses))

    if start_date:
        start_dt = datetime.combine(start_date, time.min, tzinfo=UTC)
        query = query.where(Appointment.appointment_date >= start_dt)
        count_query = count_query.where(Appointment.appointment_date >= start_dt)

    if end_date:
        end_dt = datetime.combine(end_date, time.max, tzinfo=UTC)
        query = query.where(Appointment.appointment_date <= end_dt)
        count_query = count_query.where(Appointment.appointment_date <= end_dt)

    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        # Join Customer để tìm theo mã lịch hẹn, số điện thoại hoặc tên khách hàng
        query = query.join(
            Customer, col(Appointment.customer_id) == col(Customer.id)
        ).where(
            or_(
                col(Appointment.appointment_number).ilike(search_pattern),
                col(Customer.phone_number).ilike(search_pattern),
                col(Customer.full_name).ilike(search_pattern),
            )
        )
        count_query = count_query.join(
            Customer, col(Appointment.customer_id) == col(Customer.id)
        ).where(
            or_(
                col(Appointment.appointment_number).ilike(search_pattern),
                col(Customer.phone_number).ilike(search_pattern),
                col(Customer.full_name).ilike(search_pattern),
            )
        )

    total_count = session.exec(count_query).one()

    appointments = session.exec(
        query.order_by(
            col(Appointment.appointment_date).desc(),
            col(Appointment.created_at).desc(),
        )
        .offset(skip)
        .limit(limit)
    ).all()

    details = [build_appointment_history_detail(session, appt) for appt in appointments]

    return AppointmentsHistoryPublic(
        data=details,
        count=total_count,
    )


def lookup_appointments(
    session: Session,
    appointment_number: str | None = None,
    phone_number: str | None = None,
    current_user: User | None = None,
) -> list[AppointmentHistoryDetail]:
    """Tra cứu nhanh lịch hẹn theo mã lịch hẹn hoặc số điện thoại khách hàng."""
    if not appointment_number and not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần cung cấp mã lịch hẹn (appointment_number) hoặc số điện thoại (phone_number)",
        )

    query = select(Appointment)

    if appointment_number and appointment_number.strip():
        query = query.where(
            col(Appointment.appointment_number).ilike(f"%{appointment_number.strip()}%")
        )

    if phone_number and phone_number.strip():
        query = query.join(
            Customer, col(Appointment.customer_id) == col(Customer.id)
        ).where(col(Customer.phone_number) == phone_number.strip())

    # Phân quyền: nếu là customer, chỉ trả về lịch hẹn của chính họ
    if current_user and not current_user.is_superuser:
        role = (current_user.role or "").lower()
        if role == "customer":
            user_cust = session.exec(
                select(Customer).where(Customer.user_id == current_user.id)
            ).first()
            if not user_cust:
                return []
            query = query.where(Appointment.customer_id == user_cust.id)

    appts = session.exec(
        query.order_by(col(Appointment.appointment_date).desc()).limit(20)
    ).all()

    return [build_appointment_history_detail(session, appt) for appt in appts]


def get_appointment_detail(
    session: Session,
    appointment_id: uuid.UUID,
    current_user: User | None = None,
) -> AppointmentHistoryDetail:
    """Xem thông tin chi tiết một lịch hẹn với phân quyền phù hợp."""
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch hẹn",
        )

    # Phân quyền: customer chỉ được xem lịch hẹn của mình
    if current_user and not current_user.is_superuser:
        role = (current_user.role or "").lower()
        if role == "customer":
            customer = session.get(Customer, appointment.customer_id)
            if not customer or customer.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Không có quyền xem chi tiết lịch hẹn này",
                )

    return build_appointment_history_detail(session, appointment)


def get_customer_appointment_history(
    session: Session,
    customer_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
    status_filter: str | None = None,
    current_user: User | None = None,
) -> AppointmentsHistoryPublic:
    """Lấy danh sách lịch sử sửa chữa của một khách hàng cụ thể."""
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin khách hàng",
        )

    # Phân quyền: customer chỉ được xem của chính mình
    if current_user and not current_user.is_superuser:
        role = (current_user.role or "").lower()
        if role == "customer" and customer.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền xem lịch sử lịch hẹn của khách hàng này",
            )

    query = select(Appointment).where(Appointment.customer_id == customer_id)
    count_query = (
        select(func.count())
        .select_from(Appointment)
        .where(Appointment.customer_id == customer_id)
    )

    if status_filter and status_filter.strip():
        query = query.where(Appointment.status == status_filter.strip().upper())
        count_query = count_query.where(
            Appointment.status == status_filter.strip().upper()
        )

    total_count = session.exec(count_query).one()
    appts = session.exec(
        query.order_by(col(Appointment.appointment_date).desc())
        .offset(skip)
        .limit(limit)
    ).all()

    return AppointmentsHistoryPublic(
        data=[build_appointment_history_detail(session, a) for a in appts],
        count=total_count,
    )
