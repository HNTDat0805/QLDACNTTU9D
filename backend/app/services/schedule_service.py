import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    AppointmentService,
    Message,
    Service,
    Technician,
    TechnicianSchedule,
    TechnicianScheduleCreate,
    TechnicianSchedulePublic,
    TechnicianSchedulesPublic,
    TechnicianScheduleUpdate,
    get_datetime_utc,
)

logger = get_logger("app.services.schedule_service")


def get_appointment_duration(session: Session, appointment_id: uuid.UUID) -> int:
    """Tính tổng thời gian (phút) của các dịch vụ trong lịch hẹn."""
    durations = session.exec(
        select(Service.estimated_duration_minutes)
        .join(AppointmentService)
        .where(AppointmentService.appointment_id == appointment_id)
    ).all()
    return sum(durations) if durations else 30


def check_schedule_overlap(
    session: Session,
    technician_id: uuid.UUID,
    work_date: date,
    start_time: time,
    end_time: time,
    exclude_schedule_id: uuid.UUID | None = None,
) -> bool:
    """Kiểm tra xem ca làm việc mới có bị trùng giờ với ca làm việc khác của cùng kỹ thuật viên không."""
    query = (
        select(TechnicianSchedule)
        .where(TechnicianSchedule.technician_id == technician_id)
        .where(TechnicianSchedule.work_date == work_date)
        .where(TechnicianSchedule.start_time < end_time)
        .where(TechnicianSchedule.end_time > start_time)
    )
    if exclude_schedule_id:
        query = query.where(TechnicianSchedule.id != exclude_schedule_id)

    conflict = session.exec(query).first()
    return conflict is not None


def get_conflicting_appointments(
    session: Session,
    technician_id: uuid.UUID,
    work_date: date,
    start_time: time,
    end_time: time,
) -> list[Appointment]:
    """Tìm các lịch hẹn của kỹ thuật viên nằm trong khoảng thời gian xác định."""
    day_start = datetime.combine(work_date, time.min, tzinfo=UTC)
    day_end = datetime.combine(work_date, time.max, tzinfo=UTC)

    appointments = session.exec(
        select(Appointment)
        .where(Appointment.technician_id == technician_id)
        .where(Appointment.status != "CANCELLED")
        .where(Appointment.appointment_date >= day_start)
        .where(Appointment.appointment_date <= day_end)
    ).all()

    conflicts: list[Appointment] = []
    window_start_dt = datetime.combine(work_date, start_time, tzinfo=UTC)
    window_end_dt = datetime.combine(work_date, end_time, tzinfo=UTC)

    for appt in appointments:
        appt_dt = appt.appointment_date
        if appt_dt.tzinfo is None:
            appt_dt = appt_dt.replace(tzinfo=UTC)
        duration = get_appointment_duration(session, appt.id)
        appt_end_dt = appt_dt + timedelta(minutes=duration)

        if appt_dt < window_end_dt and appt_end_dt > window_start_dt:
            conflicts.append(appt)

    return conflicts


def get_work_schedules(
    session: Session,
    skip: int = 0,
    limit: int = 50,
    technician_id: uuid.UUID | None = None,
    work_date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    status_filter: str | None = None,
) -> TechnicianSchedulesPublic:
    """Lấy danh sách ca làm việc của kỹ thuật viên với các bộ lọc linh hoạt."""
    query = select(TechnicianSchedule)
    count_query = select(func.count()).select_from(TechnicianSchedule)

    if technician_id:
        query = query.where(TechnicianSchedule.technician_id == technician_id)
        count_query = count_query.where(
            TechnicianSchedule.technician_id == technician_id
        )

    if work_date:
        query = query.where(TechnicianSchedule.work_date == work_date)
        count_query = count_query.where(TechnicianSchedule.work_date == work_date)
    else:
        if start_date:
            query = query.where(TechnicianSchedule.work_date >= start_date)
            count_query = count_query.where(TechnicianSchedule.work_date >= start_date)
        if end_date:
            query = query.where(TechnicianSchedule.work_date <= end_date)
            count_query = count_query.where(TechnicianSchedule.work_date <= end_date)

    if status_filter and status_filter.strip():
        query = query.where(TechnicianSchedule.status == status_filter.strip().upper())
        count_query = count_query.where(
            TechnicianSchedule.status == status_filter.strip().upper()
        )

    total_count = session.exec(count_query).one()
    items = session.exec(
        query.order_by(
            col(TechnicianSchedule.work_date).asc(),
            col(TechnicianSchedule.start_time).asc(),
        )
        .offset(skip)
        .limit(limit)
    ).all()

    return TechnicianSchedulesPublic(
        data=[TechnicianSchedulePublic.model_validate(s) for s in items],
        count=total_count,
    )


def create_work_schedule(
    session: Session,
    data: TechnicianScheduleCreate,
) -> TechnicianSchedulePublic:
    """Tạo lịch làm việc mới sau khi kiểm tra tính hợp lệ và xung đột trùng lặp."""
    tech = session.get(Technician, data.technician_id)
    if not tech:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy kỹ thuật viên",
        )
    if not tech.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kỹ thuật viên hiện không hoạt động",
        )

    if data.end_time <= data.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giờ kết thúc ca làm việc phải sau giờ bắt đầu",
        )

    # Kiểm tra trùng ca với các lịch làm việc khác
    has_overlap = check_schedule_overlap(
        session=session,
        technician_id=data.technician_id,
        work_date=data.work_date,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    if has_overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Đã tồn tại ca làm việc trùng lặp trong khung giờ này của kỹ thuật viên",
        )

    schedule = TechnicianSchedule(
        technician_id=data.technician_id,
        work_date=data.work_date,
        start_time=data.start_time,
        end_time=data.end_time,
        status=data.status.upper() if data.status else "AVAILABLE",
        notes=data.notes.strip() if data.notes else None,
        created_at=get_datetime_utc(),
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    return TechnicianSchedulePublic.model_validate(schedule)


def get_work_schedule_by_id(
    session: Session,
    schedule_id: uuid.UUID,
) -> TechnicianSchedulePublic:
    """Lấy chi tiết một lịch làm việc theo ID."""
    schedule = session.get(TechnicianSchedule, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch làm việc",
        )
    return TechnicianSchedulePublic.model_validate(schedule)


def update_work_schedule(
    session: Session,
    schedule_id: uuid.UUID,
    data: TechnicianScheduleUpdate,
) -> TechnicianSchedulePublic:
    """Cập nhật thông tin ca làm việc với kiểm tra xung đột lịch làm việc và lịch hẹn."""
    schedule = session.exec(
        select(TechnicianSchedule)
        .where(TechnicianSchedule.id == schedule_id)
        .with_for_update()
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch làm việc",
        )

    target_date = data.work_date if data.work_date is not None else schedule.work_date
    target_start = (
        data.start_time if data.start_time is not None else schedule.start_time
    )
    target_end = data.end_time if data.end_time is not None else schedule.end_time
    target_status = data.status.upper() if data.status is not None else schedule.status

    if target_end <= target_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giờ kết thúc ca làm việc phải sau giờ bắt đầu",
        )

    # Kiểm tra trùng ca với lịch làm việc khác của cùng kỹ thuật viên
    has_overlap = check_schedule_overlap(
        session=session,
        technician_id=schedule.technician_id,
        work_date=target_date,
        start_time=target_start,
        end_time=target_end,
        exclude_schedule_id=schedule.id,
    )
    if has_overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Khung giờ mới bị trùng với một ca làm việc khác của kỹ thuật viên",
        )

    # Kiểm tra nếu chuyển sang OFF hoặc co hẹp khung giờ thì có làm mất lịch hẹn đang có không
    if target_status == "OFF":
        conflicts = get_conflicting_appointments(
            session=session,
            technician_id=schedule.technician_id,
            work_date=schedule.work_date,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
        )
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Không thể chuyển trạng thái sang OFF vì kỹ thuật viên đã có {len(conflicts)} lịch hẹn trong ca này",
            )

    update_dict = data.model_dump(exclude_unset=True)
    if "status" in update_dict and update_dict["status"]:
        update_dict["status"] = update_dict["status"].upper()

    schedule.sqlmodel_update(update_dict)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    return TechnicianSchedulePublic.model_validate(schedule)


def update_work_schedule_status(
    session: Session,
    schedule_id: uuid.UUID,
    status_val: str,
    notes: str | None = None,
) -> TechnicianSchedulePublic:
    """Cập nhật nhanh trạng thái ca làm việc (AVAILABLE, BUSY, OFF)."""
    norm_status = status_val.strip().upper()
    if norm_status not in ("AVAILABLE", "BUSY", "OFF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trạng thái không hợp lệ. Chỉ chấp nhận AVAILABLE, BUSY, OFF",
        )

    schedule = session.exec(
        select(TechnicianSchedule)
        .where(TechnicianSchedule.id == schedule_id)
        .with_for_update()
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch làm việc",
        )

    if norm_status == "OFF":
        conflicts = get_conflicting_appointments(
            session=session,
            technician_id=schedule.technician_id,
            work_date=schedule.work_date,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
        )
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Không thể chuyển sang trạng thái OFF vì kỹ thuật viên có {len(conflicts)} lịch hẹn trong ca làm việc này",
            )

    schedule.status = norm_status
    if notes is not None:
        schedule.notes = notes.strip() if notes else None

    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    return TechnicianSchedulePublic.model_validate(schedule)


def delete_work_schedule(
    session: Session,
    schedule_id: uuid.UUID,
) -> Message:
    """Xóa ca làm việc nếu không có lịch hẹn nào đang được phân công trong ca đó."""
    schedule = session.get(TechnicianSchedule, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch làm việc",
        )

    conflicts = get_conflicting_appointments(
        session=session,
        technician_id=schedule.technician_id,
        work_date=schedule.work_date,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
    )
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Không thể xóa ca làm việc vì kỹ thuật viên có {len(conflicts)} lịch hẹn cần xử lý trong khung giờ này",
        )

    session.delete(schedule)
    session.commit()
    return Message(message="Lịch làm việc đã được xóa thành công")
