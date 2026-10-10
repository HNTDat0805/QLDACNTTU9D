import secrets
import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlmodel import Session, col, select

from app.models import (
    Appointment,
    AppointmentBookingCreate,
    AppointmentBookingResponse,
    AppointmentBookingUpdate,
    AppointmentService,
    AvailableSlotItem,
    AvailableSlotsResponse,
    Customer,
    Device,
    RepairStatusHistory,
    Service,
    SlotCheckRequest,
    SlotCheckResponse,
    Technician,
    TechnicianSchedule,
)


def generate_appointment_code(session: Session, appt_date: date) -> str:
    """Generate a unique appointment code such as APPT-20261015-A1B2."""
    date_str = appt_date.strftime("%Y%m%d")
    for _ in range(10):
        random_suffix = secrets.token_hex(2).upper()
        candidate = f"APPT-{date_str}-{random_suffix}"
        existing = session.exec(
            select(Appointment).where(Appointment.appointment_number == candidate)
        ).first()
        if not existing:
            return candidate
    return f"APPT-{date_str}-{uuid.uuid4().hex[:6].upper()}"


def get_appointment_duration(session: Session, appointment_id: uuid.UUID) -> int:
    """Calculate appointment duration in minutes based on its linked services."""
    svc_durations = session.exec(
        select(Service.estimated_duration_minutes)
        .join(AppointmentService)
        .where(AppointmentService.appointment_id == appointment_id)
    ).all()
    return sum(svc_durations) if svc_durations else 30


def check_overlap(
    session: Session,
    technician_id: uuid.UUID,
    slot_start: datetime,
    slot_end: datetime,
    exclude_appt_id: uuid.UUID | None = None,
) -> bool:
    """Check if a technician has any overlapping non-cancelled appointment.

    Interval overlap formula: slot_start < appt_end and slot_end > appt_start.
    """
    day_start = datetime.combine(slot_start.date(), time.min, tzinfo=UTC)
    day_end = datetime.combine(slot_start.date(), time.max, tzinfo=UTC)

    query = (
        select(Appointment)
        .where(Appointment.technician_id == technician_id)
        .where(Appointment.status != "CANCELLED")
        .where(Appointment.appointment_date >= day_start)
        .where(Appointment.appointment_date <= day_end)
    )
    if exclude_appt_id:
        query = query.where(Appointment.id != exclude_appt_id)

    appts = session.exec(query).all()
    for appt in appts:
        appt_duration = get_appointment_duration(session, appt.id)
        appt_start = appt.appointment_date
        if appt_start.tzinfo is None:
            appt_start = appt_start.replace(tzinfo=UTC)
        appt_end = appt_start + timedelta(minutes=appt_duration)

        if slot_start < appt_end and slot_end > appt_start:
            return True
    return False


def get_available_slots(
    session: Session,
    slot_date: date,
    service_id: uuid.UUID,
    technician_id: uuid.UUID | None = None,
    slot_duration: int | None = None,
) -> AvailableSlotsResponse:
    """API 1: Query available booking slots for a given date, service, and technician."""
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy dịch vụ"
        )
    if not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dịch vụ hiện không hoạt động",
        )

    duration_minutes = service.estimated_duration_minutes
    if slot_duration and slot_duration > 0:
        duration_minutes = max(service.estimated_duration_minutes, slot_duration)

    step_minutes = (
        slot_duration
        if (slot_duration and slot_duration > 0)
        else min(30, duration_minutes)
    )

    # Determine technicians to check
    techs: list[Technician] = []
    if technician_id:
        tech = session.get(Technician, technician_id)
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy kỹ thuật viên",
            )
        if not tech.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kỹ thuật viên không còn hoạt động",
            )
        techs = [tech]
    else:
        techs = list(
            session.exec(
                select(Technician)
                .join(TechnicianSchedule)
                .where(col(Technician.is_active).is_(True))
                .where(TechnicianSchedule.work_date == slot_date)
                .where(TechnicianSchedule.status == "AVAILABLE")
                .distinct()
            ).all()
        )

    if not techs:
        return AvailableSlotsResponse(
            date=slot_date, service_id=service_id, available_slots=[]
        )

    unique_slots: dict[tuple[str, str], AvailableSlotItem] = {}

    for tech in techs:
        schedules = session.exec(
            select(TechnicianSchedule)
            .where(TechnicianSchedule.technician_id == tech.id)
            .where(TechnicianSchedule.work_date == slot_date)
            .where(TechnicianSchedule.status == "AVAILABLE")
            .order_by(col(TechnicianSchedule.start_time))
        ).all()

        for sch in schedules:
            shift_start_dt = datetime.combine(slot_date, sch.start_time, tzinfo=UTC)
            shift_end_dt = datetime.combine(slot_date, sch.end_time, tzinfo=UTC)

            current_start_dt = shift_start_dt
            while (
                current_start_dt + timedelta(minutes=duration_minutes) <= shift_end_dt
            ):
                current_end_dt = current_start_dt + timedelta(minutes=duration_minutes)

                # Check conflict with existing appointments
                has_conflict = check_overlap(
                    session, tech.id, current_start_dt, current_end_dt
                )
                if not has_conflict:
                    start_str = current_start_dt.strftime("%H:%M")
                    end_str = current_end_dt.strftime("%H:%M")
                    key = (start_str, end_str)
                    if key not in unique_slots:
                        unique_slots[key] = AvailableSlotItem(
                            start_time=start_str,
                            end_time=end_str,
                            available=True,
                            technician_id=tech.id if technician_id else None,
                        )

                current_start_dt += timedelta(minutes=step_minutes)

    sorted_slots = sorted(unique_slots.values(), key=lambda s: s.start_time)
    return AvailableSlotsResponse(
        date=slot_date, service_id=service_id, available_slots=sorted_slots
    )


def check_slot_availability(
    session: Session, data: SlotCheckRequest
) -> SlotCheckResponse:
    """API 4: Verify whether a specific time slot is available for booking."""
    service = session.get(Service, data.service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy dịch vụ"
        )
    if not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dịch vụ hiện không hoạt động",
        )

    duration_minutes = service.estimated_duration_minutes
    slot_start_dt = datetime.combine(data.appointment_date, data.start_time, tzinfo=UTC)
    slot_end_dt = slot_start_dt + timedelta(minutes=duration_minutes)
    start_str = data.start_time.strftime("%H:%M")
    end_str = slot_end_dt.strftime("%H:%M")

    # Specific technician requested
    if data.technician_id:
        tech = session.get(Technician, data.technician_id)
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy kỹ thuật viên",
            )
        if not tech.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kỹ thuật viên không hoạt động",
            )

        # Check working schedule covers the requested window
        schedule = session.exec(
            select(TechnicianSchedule)
            .where(TechnicianSchedule.technician_id == tech.id)
            .where(TechnicianSchedule.work_date == data.appointment_date)
            .where(TechnicianSchedule.status == "AVAILABLE")
            .where(TechnicianSchedule.start_time <= data.start_time)
            .where(TechnicianSchedule.end_time >= slot_end_dt.time())
        ).first()

        if not schedule:
            return SlotCheckResponse(
                available=False,
                reason="TECHNICIAN_NOT_WORKING",
                message="Kỹ thuật viên không có lịch làm việc trong khung giờ này",
                start_time=start_str,
                end_time=end_str,
                technician_id=tech.id,
            )

        # Check appointment conflict
        if check_overlap(
            session,
            tech.id,
            slot_start_dt,
            slot_end_dt,
            exclude_appt_id=data.exclude_appointment_id,
        ):
            return SlotCheckResponse(
                available=False,
                reason="SLOT_UNAVAILABLE",
                message="Khung giờ đã có lịch hẹn khác",
                start_time=start_str,
                end_time=end_str,
                technician_id=tech.id,
            )

        return SlotCheckResponse(
            available=True,
            reason=None,
            message=None,
            start_time=start_str,
            end_time=end_str,
            technician_id=tech.id,
        )

    # Auto-assignment: Find any active technician with coverage
    schedules = session.exec(
        select(TechnicianSchedule)
        .join(Technician)
        .where(col(Technician.is_active).is_(True))
        .where(TechnicianSchedule.work_date == data.appointment_date)
        .where(TechnicianSchedule.status == "AVAILABLE")
        .where(TechnicianSchedule.start_time <= data.start_time)
        .where(TechnicianSchedule.end_time >= slot_end_dt.time())
    ).all()

    if not schedules:
        return SlotCheckResponse(
            available=False,
            reason="NO_TECHNICIAN_AVAILABLE",
            message="Không có kỹ thuật viên làm việc trong khung giờ này",
            start_time=start_str,
            end_time=end_str,
        )

    for sch in schedules:
        if not check_overlap(
            session,
            sch.technician_id,
            slot_start_dt,
            slot_end_dt,
            exclude_appt_id=data.exclude_appointment_id,
        ):
            return SlotCheckResponse(
                available=True,
                reason=None,
                message=None,
                start_time=start_str,
                end_time=end_str,
                technician_id=sch.technician_id,
            )

    return SlotCheckResponse(
        available=False,
        reason="SLOT_UNAVAILABLE",
        message="Tất cả kỹ thuật viên đều bận trong khung giờ này",
        start_time=start_str,
        end_time=end_str,
    )


def create_booking_appointment(
    session: Session, data: AppointmentBookingCreate
) -> AppointmentBookingResponse:
    """API 2: Create a new repair appointment with atomic concurrency locking."""
    customer = session.get(Customer, data.customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khách hàng"
        )

    # Resolve or create customer device
    device: Device | None = None
    if data.device_id:
        device = session.get(Device, data.device_id)
        if not device or device.customer_id != customer.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy thiết bị hợp lệ của khách hàng",
            )
    else:
        # Use existing device or create default
        device = session.exec(
            select(Device).where(Device.customer_id == customer.id)
        ).first()
        if not device:
            device = Device(
                customer_id=customer.id,
                device_type="Smartphone",
                brand=data.device_brand or "Generic",
                model=data.device_model or "Smartphone",
            )
            session.add(device)
            session.flush()

    service = session.get(Service, data.service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy dịch vụ"
        )
    if not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dịch vụ hiện không hoạt động",
        )

    duration_minutes = service.estimated_duration_minutes
    slot_start_dt = datetime.combine(data.appointment_date, data.start_time, tzinfo=UTC)
    slot_end_dt = slot_start_dt + timedelta(minutes=duration_minutes)
    end_time = slot_end_dt.time()

    assigned_tech_id: uuid.UUID | None = None

    if data.technician_id:
        tech = session.exec(
            select(Technician)
            .where(Technician.id == data.technician_id)
            .with_for_update()
        ).first()
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy kỹ thuật viên",
            )
        if not tech.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kỹ thuật viên không hoạt động",
            )

        schedule = session.exec(
            select(TechnicianSchedule)
            .where(TechnicianSchedule.technician_id == tech.id)
            .where(TechnicianSchedule.work_date == data.appointment_date)
            .where(TechnicianSchedule.status == "AVAILABLE")
            .where(TechnicianSchedule.start_time <= data.start_time)
            .where(TechnicianSchedule.end_time >= end_time)
        ).first()
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kỹ thuật viên không có ca làm việc phù hợp trong khung giờ này",
            )

        if check_overlap(session, tech.id, slot_start_dt, slot_end_dt):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Khung giờ đã có lịch hẹn khác",
            )
        assigned_tech_id = tech.id
    else:
        # Auto-assignment: Find candidate technicians and lock row
        candidates = list(
            session.exec(
                select(TechnicianSchedule)
                .join(Technician)
                .where(col(Technician.is_active).is_(True))
                .where(TechnicianSchedule.work_date == data.appointment_date)
                .where(TechnicianSchedule.status == "AVAILABLE")
                .where(TechnicianSchedule.start_time <= data.start_time)
                .where(TechnicianSchedule.end_time >= end_time)
            ).all()
        )
        if not candidates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không có kỹ thuật viên nào làm việc trong khung giờ này",
            )

        for sch in candidates:
            cand_tech = session.exec(
                select(Technician)
                .where(Technician.id == sch.technician_id)
                .with_for_update()
            ).first()
            if not cand_tech:
                continue
            if not check_overlap(session, cand_tech.id, slot_start_dt, slot_end_dt):
                assigned_tech_id = cand_tech.id
                break

        if not assigned_tech_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tất cả kỹ thuật viên đều đã kín lịch trong khung giờ này",
            )

    appt_code = generate_appointment_code(session, data.appointment_date)

    appointment = Appointment(
        appointment_number=appt_code,
        customer_id=customer.id,
        device_id=device.id,
        technician_id=assigned_tech_id,
        appointment_date=slot_start_dt,
        status="PENDING",
        customer_notes=data.description,
        total_amount=service.base_price,
    )
    session.add(appointment)
    session.flush()

    appt_service = AppointmentService(
        appointment_id=appointment.id,
        service_id=service.id,
        price_at_booking=service.base_price,
        quantity=1,
    )
    session.add(appt_service)

    history = RepairStatusHistory(
        appointment_id=appointment.id,
        previous_status=None,
        new_status="PENDING",
        note="Tạo lịch hẹn thành công",
    )
    session.add(history)

    session.commit()
    session.refresh(appointment)

    return AppointmentBookingResponse(
        appointment_id=appointment.id,
        appointment_code=appointment.appointment_number,
        appointment_date=data.appointment_date,
        start_time=data.start_time.strftime("%H:%M"),
        status=appointment.status,
        message="Tạo lịch hẹn thành công",
    )


def update_booking_appointment(
    session: Session,
    appointment_id: uuid.UUID,
    data: AppointmentBookingUpdate,
) -> AppointmentBookingResponse:
    """API 3: Update an existing appointment (reschedule or change technician)."""
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lịch hẹn"
        )

    if (appointment.status or "").upper() in ("CANCELLED", "COMPLETED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể cập nhật lịch hẹn đã hoàn thành hoặc đã bị hủy",
        )

    # Determine if rescheduling date/time or changing technician
    is_rescheduling = (
        data.appointment_date is not None
        or data.start_time is not None
        or data.technician_id is not None
    )

    if is_rescheduling:
        existing_dt = appointment.appointment_date
        if existing_dt.tzinfo is None:
            existing_dt = existing_dt.replace(tzinfo=UTC)

        target_date = (
            data.appointment_date
            if data.appointment_date is not None
            else existing_dt.date()
        )
        target_time = (
            data.start_time if data.start_time is not None else existing_dt.time()
        )
        target_tech_id = (
            data.technician_id
            if data.technician_id is not None
            else appointment.technician_id
        )

        duration = get_appointment_duration(session, appointment.id)
        target_start_dt = datetime.combine(target_date, target_time, tzinfo=UTC)
        target_end_dt = target_start_dt + timedelta(minutes=duration)
        target_end_time = target_end_dt.time()

        if target_tech_id:
            tech = session.exec(
                select(Technician)
                .where(Technician.id == target_tech_id)
                .with_for_update()
            ).first()
            if not tech:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy kỹ thuật viên",
                )
            if not tech.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Kỹ thuật viên không hoạt động",
                )

            schedule = session.exec(
                select(TechnicianSchedule)
                .where(TechnicianSchedule.technician_id == tech.id)
                .where(TechnicianSchedule.work_date == target_date)
                .where(TechnicianSchedule.status == "AVAILABLE")
                .where(TechnicianSchedule.start_time <= target_time)
                .where(TechnicianSchedule.end_time >= target_end_time)
            ).first()
            if not schedule:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Kỹ thuật viên không có ca làm việc phù hợp trong khung giờ này",
                )

            # Exclude current appointment from conflict check
            if check_overlap(
                session,
                tech.id,
                target_start_dt,
                target_end_dt,
                exclude_appt_id=appointment.id,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Khung giờ mới đã bị trùng với lịch hẹn khác",
                )

            appointment.technician_id = tech.id
        else:
            # Reassign if technician wasn't set
            pass

        appointment.appointment_date = target_start_dt

    if data.description is not None:
        appointment.customer_notes = data.description

    history = RepairStatusHistory(
        appointment_id=appointment.id,
        previous_status=appointment.status,
        new_status=appointment.status,
        note="Cập nhật thông tin lịch hẹn",
    )
    session.add(history)

    session.commit()
    session.refresh(appointment)

    appt_dt = appointment.appointment_date
    if appt_dt.tzinfo is None:
        appt_dt = appt_dt.replace(tzinfo=UTC)

    return AppointmentBookingResponse(
        appointment_id=appointment.id,
        appointment_code=appointment.appointment_number,
        appointment_date=appt_dt.date(),
        start_time=appt_dt.time().strftime("%H:%M"),
        status=appointment.status,
        message="Cập nhật lịch hẹn thành công",
    )
