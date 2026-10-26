import uuid
from datetime import UTC, date, datetime, time

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlmodel import Session, col, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    AppointmentBookingCreate,
    AppointmentBookingResponse,
    AppointmentService,
    AppointmentStatus,
    Customer,
    Device,
    QueueItemPublic,
    QueueListResponse,
    QueueStatusUpdate,
    RepairStatusHistory,
    Service,
    Technician,
    User,
    get_datetime_utc,
)
from app.services import slot_service

logger = get_logger("app.services.queue_service")

ACTIVE_QUEUE_STATUSES = [
    AppointmentStatus.PENDING.value,
    AppointmentStatus.CONFIRMED.value,
    AppointmentStatus.IN_PROGRESS.value,
]


def _build_queue_item(
    session: Session,
    appointment: Appointment,
    position: int,
) -> QueueItemPublic:
    """Helper xây dựng đối tượng QueueItemPublic từ Appointment và các bảng liên kết."""
    customer = session.get(Customer, appointment.customer_id)
    device = session.get(Device, appointment.device_id)
    tech = (
        session.get(Technician, appointment.technician_id)
        if appointment.technician_id
        else None
    )

    services_data = session.exec(
        select(Service.name, Service.estimated_duration_minutes)
        .join(AppointmentService)
        .where(AppointmentService.appointment_id == appointment.id)
    ).all()

    service_names = [s[0] for s in services_data] if services_data else []
    duration = sum(s[1] for s in services_data) if services_data else 30

    device_str = (
        f"{device.brand} {device.model}".strip() if device else "Không xác định"
    )

    return QueueItemPublic(
        appointment_id=appointment.id,
        appointment_number=appointment.appointment_number,
        status=appointment.status,
        appointment_date=appointment.appointment_date,
        customer_id=appointment.customer_id,
        customer_name=customer.full_name if customer else "Khách hàng",
        customer_phone=customer.phone_number if customer else "",
        device_id=appointment.device_id,
        device_info=device_str,
        technician_id=appointment.technician_id,
        technician_name=tech.full_name if tech else None,
        service_names=service_names,
        total_amount=appointment.total_amount,
        estimated_duration_minutes=duration,
        queue_position=position,
        technician_diagnosis=appointment.technician_diagnosis,
        customer_notes=appointment.customer_notes,
        created_at=appointment.created_at,
    )


def get_queue_list(
    session: Session,
    skip: int = 0,
    limit: int = 50,
    queue_date: date | None = None,
    status_filter: str | None = None,
    technician_id: uuid.UUID | None = None,
) -> QueueListResponse:
    """Lấy danh sách các lịch hẹn đang trong hàng chờ kèm số thứ tự vị trí."""
    query = select(Appointment)
    count_query = select(func.count()).select_from(Appointment)

    # Mặc định chỉ lấy các trạng thái đang hoạt động trong hàng chờ
    if status_filter and status_filter.strip():
        norm_status = status_filter.strip().upper()
        query = query.where(Appointment.status == norm_status)
        count_query = count_query.where(Appointment.status == norm_status)
    else:
        query = query.where(col(Appointment.status).in_(ACTIVE_QUEUE_STATUSES))
        count_query = count_query.where(
            col(Appointment.status).in_(ACTIVE_QUEUE_STATUSES)
        )

    if queue_date:
        day_start = datetime.combine(queue_date, time.min, tzinfo=UTC)
        day_end = datetime.combine(queue_date, time.max, tzinfo=UTC)
        query = query.where(
            Appointment.appointment_date >= day_start,
            Appointment.appointment_date <= day_end,
        )
        count_query = count_query.where(
            Appointment.appointment_date >= day_start,
            Appointment.appointment_date <= day_end,
        )

    if technician_id:
        query = query.where(Appointment.technician_id == technician_id)
        count_query = count_query.where(Appointment.technician_id == technician_id)

    total_count = session.exec(count_query).one()

    # Sắp xếp theo thứ tự ưu tiên nghiệp vụ: thời gian hẹn tăng dần, thời điểm tạo tăng dần
    appts = session.exec(
        query.order_by(
            col(Appointment.appointment_date).asc(),
            col(Appointment.created_at).asc(),
        )
        .offset(skip)
        .limit(limit)
    ).all()

    queue_items: list[QueueItemPublic] = []
    for idx, appt in enumerate(appts):
        pos = skip + idx + 1
        queue_items.append(_build_queue_item(session, appt, pos))

    return QueueListResponse(
        data=queue_items,
        count=total_count,
        date=queue_date,
    )


def get_queue_item(
    session: Session,
    appointment_id: uuid.UUID,
) -> QueueItemPublic:
    """Xem chi tiết 1 mục trong hàng chờ và tính vị trí thứ tự hiện tại của nó."""
    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch hẹn",
        )

    if appt.status not in ACTIVE_QUEUE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lịch hẹn không nằm trong hàng chờ hoạt động (trạng thái: {appt.status})",
        )

    # Tính thứ tự vị trí hàng chờ
    earlier_count = session.exec(
        select(func.count())
        .select_from(Appointment)
        .where(col(Appointment.status).in_(ACTIVE_QUEUE_STATUSES))
        .where(
            or_(
                col(Appointment.appointment_date) < appt.appointment_date,
                (
                    (col(Appointment.appointment_date) == appt.appointment_date)
                    & (col(Appointment.created_at) < appt.created_at)
                ),
            )
        )
    ).one()

    return _build_queue_item(session, appt, position=earlier_count + 1)


def add_to_queue(
    session: Session,
    data: AppointmentBookingCreate,
) -> AppointmentBookingResponse:
    """Thêm lịch hẹn vào hàng chờ bằng cách tạo mới lịch hẹn tiếp nhận qua slot_service."""
    return slot_service.create_booking_appointment(session=session, data=data)


def update_queue_status(
    session: Session,
    appointment_id: uuid.UUID,
    data: QueueStatusUpdate,
    current_user: User,
) -> QueueItemPublic:
    """Cập nhật trạng thái xử lý hàng chờ và tự động lưu lịch sử RepairStatusHistory."""
    appointment = session.exec(
        select(Appointment).where(Appointment.id == appointment_id).with_for_update()
    ).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch hẹn trong hàng chờ",
        )

    old_status = (appointment.status or "").upper()
    new_status = data.status.strip().upper()

    valid_statuses = [
        AppointmentStatus.PENDING.value,
        AppointmentStatus.CONFIRMED.value,
        AppointmentStatus.IN_PROGRESS.value,
        AppointmentStatus.COMPLETED.value,
        AppointmentStatus.CANCELLED.value,
    ]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trạng thái '{new_status}' không hợp lệ",
        )

    if old_status in ("COMPLETED", "CANCELLED"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Không thể cập nhật lịch hẹn đã kết thúc (trạng thái hiện tại: {old_status})",
        )

    # Cập nhật kỹ thuật viên nếu có truyền vào
    if data.technician_id:
        tech = session.get(Technician, data.technician_id)
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy kỹ thuật viên được phân công",
            )
        if not tech.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kỹ thuật viên được phân công hiện không hoạt động",
            )
        appointment.technician_id = tech.id

    if data.technician_diagnosis is not None:
        appointment.technician_diagnosis = data.technician_diagnosis.strip()

    if new_status == AppointmentStatus.COMPLETED.value:
        appointment.actual_completion_date = get_datetime_utc()

    # Ghi nhận lịch sử chuyển trạng thái
    note_text = data.note or f"Cập nhật hàng chờ từ {old_status} sang {new_status}"
    history = RepairStatusHistory(
        appointment_id=appointment.id,
        previous_status=old_status,
        new_status=new_status,
        note=note_text,
        changed_by_user_id=current_user.id,
        created_at=get_datetime_utc(),
    )
    session.add(history)

    appointment.status = new_status
    appointment.updated_at = get_datetime_utc()
    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    # Tính vị trí nếu còn trong hàng chờ
    pos = 1
    if new_status in ACTIVE_QUEUE_STATUSES:
        earlier_count = session.exec(
            select(func.count())
            .select_from(Appointment)
            .where(col(Appointment.status).in_(ACTIVE_QUEUE_STATUSES))
            .where(
                or_(
                    col(Appointment.appointment_date) < appointment.appointment_date,
                    (
                        (
                            col(Appointment.appointment_date)
                            == appointment.appointment_date
                        )
                        & (col(Appointment.created_at) < appointment.created_at)
                    ),
                )
            )
        ).one()
        pos = earlier_count + 1

    return _build_queue_item(session, appointment, position=pos)
