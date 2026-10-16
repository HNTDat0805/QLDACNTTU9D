import secrets
import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlmodel import Session, col, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    AppointmentBookingCreate,
    AppointmentBookingResponse,
    AppointmentBookingUpdate,
    AppointmentCancelData,
    AppointmentCancelRequest,
    AppointmentCancelResponse,
    AppointmentConfirmData,
    AppointmentConfirmResponse,
    AppointmentService,
    AppointmentStatus,
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
    User,
    get_datetime_utc,
)

logger = get_logger("app.services.slot_service")


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


def check_can_update(user: User, appointment: Appointment, session: Session) -> None:
    """Validate that the user has permission to update the appointment.

    Allowed:
    - superuser, admin, manager, staff, technician
    - customer who owns the appointment (linked via customer.user_id)
    Forbidden:
    - any other user or a customer attempting to update someone else's appointment.
    """
    if user.is_superuser:
        return
    role = (user.role or "").lower()
    if role in ("admin", "manager", "staff", "technician"):
        return
    if role == "customer":
        customer = session.get(Customer, appointment.customer_id)
        if customer and customer.user_id == user.id:
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Không đủ quyền cập nhật lịch hẹn",
    )


def create_booking_appointment(
    session: Session, data: AppointmentBookingCreate
) -> AppointmentBookingResponse:
    """API 1: Create a new repair appointment with atomic concurrency locking."""
    try:
        # 1. Resolve or create customer
        customer: Customer | None = None
        if data.customer_id:
            customer = session.get(Customer, data.customer_id)
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy khách hàng",
                )
        elif data.customer_phone and data.customer_phone.strip():
            phone = data.customer_phone.strip()
            customer = session.exec(
                select(Customer).where(Customer.phone_number == phone)
            ).first()
            if not customer:
                customer = Customer(
                    full_name=data.customer_name or "Khách hàng",
                    phone_number=phone,
                    email=data.customer_email,
                    address=data.customer_address,
                )
                session.add(customer)
                session.flush()
            else:
                if data.customer_name:
                    customer.full_name = data.customer_name
                if data.customer_email:
                    customer.email = data.customer_email
                if data.customer_address:
                    customer.address = data.customer_address
                session.add(customer)
                session.flush()
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cần cung cấp thông tin khách hàng (customer_id hoặc customer_phone)",
            )

        # 2. Resolve or create customer device
        device: Device | None = None
        if data.device_id:
            device = session.get(Device, data.device_id)
            if not device or device.customer_id != customer.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy thiết bị hợp lệ của khách hàng",
                )
        else:
            device = session.exec(
                select(Device).where(Device.customer_id == customer.id)
            ).first()
            if not device:
                device = Device(
                    customer_id=customer.id,
                    device_type=data.device_type or "Smartphone",
                    brand=data.device_brand or "Generic",
                    model=data.device_model or "Smartphone",
                )
                session.add(device)
                session.flush()
            elif data.device_brand and (
                device.brand != data.device_brand
                or (data.device_model and device.model != data.device_model)
            ):
                device = Device(
                    customer_id=customer.id,
                    device_type=data.device_type or "Smartphone",
                    brand=data.device_brand,
                    model=data.device_model or "Smartphone",
                )
                session.add(device)
                session.flush()

        # 3. Resolve services
        svc_ids: list[uuid.UUID] = []
        if data.service_ids:
            svc_ids.extend(data.service_ids)
        elif data.service_id:
            svc_ids.append(data.service_id)

        if not svc_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cần chọn ít nhất một dịch vụ sửa chữa",
            )

        selected_services: list[Service] = []
        for sid in svc_ids:
            svc = session.get(Service, sid)
            if not svc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy dịch vụ",
                )
            if not svc.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dịch vụ '{svc.name}' hiện không hoạt động",
                )
            selected_services.append(svc)

        duration_minutes = sum(s.estimated_duration_minutes for s in selected_services)
        total_price = sum(s.base_price for s in selected_services)

        # 4. Check appointment date/time
        if data.appointment_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể đặt lịch trong quá khứ",
            )

        slot_start_dt = datetime.combine(
            data.appointment_date, data.start_time, tzinfo=UTC
        )
        if data.appointment_date == date.today() and slot_start_dt < get_datetime_utc():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể đặt lịch trong quá khứ",
            )

        slot_end_dt = slot_start_dt + timedelta(minutes=duration_minutes)
        end_time = slot_end_dt.time()

        # 5. Technician assignment with row lock
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
            # Auto-assignment: Find candidate technicians and lock rows in deterministic order
            candidates = list(
                session.exec(
                    select(TechnicianSchedule)
                    .join(Technician)
                    .where(col(Technician.is_active).is_(True))
                    .where(TechnicianSchedule.work_date == data.appointment_date)
                    .where(TechnicianSchedule.status == "AVAILABLE")
                    .where(TechnicianSchedule.start_time <= data.start_time)
                    .where(TechnicianSchedule.end_time >= end_time)
                    .order_by(col(TechnicianSchedule.technician_id))
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
            total_amount=total_price,
        )
        session.add(appointment)
        session.flush()

        for svc in selected_services:
            appt_service = AppointmentService(
                appointment_id=appointment.id,
                service_id=svc.id,
                price_at_booking=svc.base_price,
                quantity=1,
            )
            session.add(appt_service)

        history = RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status=None,
            new_status="PENDING",
            note="Tạo lịch hẹn thành công",
            changed_by_user_id=customer.user_id if customer else None,
        )
        session.add(history)

        session.commit()
        session.refresh(appointment)

        return AppointmentBookingResponse(
            appointment_id=appointment.id,
            appointment_code=appointment.appointment_number,
            appointment_date=data.appointment_date,
            start_time=data.start_time.strftime("%H:%M"),
            end_time=end_time.strftime("%H:%M"),
            status=appointment.status,
            message="Tạo lịch hẹn thành công",
            customer_id=customer.id,
            device_id=device.id,
            technician_id=assigned_tech_id,
            total_amount=total_price,
            service_names=[s.name for s in selected_services],
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Lỗi hệ thống khi tạo lịch hẹn: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống khi tạo lịch hẹn",
        ) from e


def update_booking_appointment(
    session: Session,
    appointment_id: uuid.UUID,
    data: AppointmentBookingUpdate,
    current_user: User | None = None,
) -> AppointmentBookingResponse:
    """API 2: Update an existing appointment (reschedule or change technician)."""
    try:
        appointment = session.exec(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
        ).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lịch hẹn"
            )

        # Authorization check
        if current_user is not None:
            check_can_update(
                user=current_user, appointment=appointment, session=session
            )

        # Status check: HTTP 409 Conflict if already cancelled, completed, or in progress
        current_status = (appointment.status or "").upper()
        if current_status in (
            AppointmentStatus.CANCELLED.value,
            AppointmentStatus.COMPLETED.value,
            AppointmentStatus.IN_PROGRESS.value,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Không thể cập nhật lịch hẹn đã hoàn thành, đang sửa chữa hoặc đã bị hủy",
            )

        # Update contact info if provided
        if data.contact_name or data.contact_phone:
            cust = session.get(Customer, appointment.customer_id)
            if cust:
                if data.contact_name:
                    cust.full_name = data.contact_name
                if data.contact_phone:
                    cust.phone_number = data.contact_phone
                session.add(cust)

        # Update device info if provided
        if data.device_brand or data.device_model:
            dev = session.get(Device, appointment.device_id)
            if dev:
                if data.device_brand:
                    dev.brand = data.device_brand
                if data.device_model:
                    dev.model = data.device_model
                session.add(dev)

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

            if target_date < date.today():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không thể đổi lịch sang ngày trong quá khứ",
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
                # Auto-assignment: Find candidate technicians and lock rows
                candidates = list(
                    session.exec(
                        select(TechnicianSchedule)
                        .join(Technician)
                        .where(col(Technician.is_active).is_(True))
                        .where(TechnicianSchedule.work_date == target_date)
                        .where(TechnicianSchedule.status == "AVAILABLE")
                        .where(TechnicianSchedule.start_time <= target_time)
                        .where(TechnicianSchedule.end_time >= target_end_time)
                        .order_by(col(TechnicianSchedule.technician_id))
                    ).all()
                )
                if not candidates:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Không có kỹ thuật viên nào làm việc trong khung giờ này",
                    )
                assigned_tech_id = None
                for sch in candidates:
                    cand_tech = session.exec(
                        select(Technician)
                        .where(Technician.id == sch.technician_id)
                        .with_for_update()
                    ).first()
                    if not cand_tech:
                        continue
                    if not check_overlap(
                        session,
                        cand_tech.id,
                        target_start_dt,
                        target_end_dt,
                        exclude_appt_id=appointment.id,
                    ):
                        assigned_tech_id = cand_tech.id
                        break
                if not assigned_tech_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Tất cả kỹ thuật viên đều đã kín lịch trong khung giờ này",
                    )
                appointment.technician_id = assigned_tech_id

            appointment.appointment_date = target_start_dt

        if data.description is not None:
            appointment.customer_notes = data.description

        appointment.updated_at = get_datetime_utc()

        audit_note = "Cập nhật thông tin lịch hẹn"
        if data.reschedule_reason:
            audit_note += f". Lý do đổi lịch: {data.reschedule_reason}"

        history = RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status=appointment.status,
            new_status=appointment.status,
            note=audit_note,
            changed_by_user_id=current_user.id if current_user else None,
        )
        session.add(history)

        session.commit()
        session.refresh(appointment)

        appt_dt = appointment.appointment_date
        if appt_dt.tzinfo is None:
            appt_dt = appt_dt.replace(tzinfo=UTC)

        duration = get_appointment_duration(session, appointment.id)
        end_dt = appt_dt + timedelta(minutes=duration)

        return AppointmentBookingResponse(
            appointment_id=appointment.id,
            appointment_code=appointment.appointment_number,
            appointment_date=appt_dt.date(),
            start_time=appt_dt.time().strftime("%H:%M"),
            end_time=end_dt.time().strftime("%H:%M"),
            status=appointment.status,
            message="Cập nhật lịch hẹn thành công",
            customer_id=appointment.customer_id,
            device_id=appointment.device_id,
            technician_id=appointment.technician_id,
            total_amount=appointment.total_amount,
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Lỗi hệ thống khi cập nhật lịch hẹn {appointment_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống khi cập nhật lịch hẹn",
        ) from e


def check_can_confirm(user: User) -> None:
    """Validate that the user has permission to confirm appointments.

    Allowed: superuser, admin, manager, staff, technician.
    Forbidden: customer.
    """
    if user.is_superuser:
        return
    role = (user.role or "").lower()
    if role in ("admin", "manager", "staff", "technician"):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Không đủ quyền xác nhận lịch hẹn",
    )


def check_can_cancel(user: User, appointment: Appointment, session: Session) -> None:
    """Validate that the user has permission to cancel the appointment.

    Allowed:
    - superuser, admin, manager, staff
    - customer who owns the appointment (linked via customer.user_id)
    Forbidden:
    - any other user or a customer attempting to cancel someone else's appointment.
    """
    if user.is_superuser:
        return
    role = (user.role or "").lower()
    if role in ("admin", "manager", "staff"):
        return
    if role == "customer":
        customer = session.get(Customer, appointment.customer_id)
        if customer and customer.user_id == user.id:
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Không đủ quyền hủy lịch hẹn",
    )


def confirm_appointment(
    session: Session,
    appointment_id: uuid.UUID,
    current_user: User,
) -> AppointmentConfirmResponse:
    """API: Xác nhận lịch hẹn.

    Quy tắc nghiệp vụ:
    1. Kiểm tra tồn tại lịch hẹn (404 Not Found).
    2. Kiểm tra quyền của người gọi (403 Forbidden).
    3. Idempotent: nếu đã xác nhận (CONFIRMED), trả về thành công không tạo tác dụng phụ.
    4. Không cho xác nhận lịch đã hủy (CANCELLED), hoàn tất (COMPLETED), hoặc đang xử lý (IN_PROGRESS) -> 409 Conflict.
    5. Cập nhật trạng thái sang CONFIRMED, lưu audit log vào RepairStatusHistory, commit transaction.
    """
    try:
        # 1. Lock appointment row for concurrency safety
        appointment = session.exec(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
        ).first()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy lịch hẹn",
            )

        # 2. Check authorization
        check_can_confirm(current_user)

        # 3. Status checks
        current_status = (appointment.status or "").upper()
        if current_status == AppointmentStatus.CONFIRMED.value:
            # Idempotent response
            return AppointmentConfirmResponse(
                success=True,
                message="Lịch hẹn đã được xác nhận trước đó",
                data=AppointmentConfirmData(
                    id=appointment.id,
                    appointment_number=appointment.appointment_number,
                    status=appointment.status,
                    appointment_date=appointment.appointment_date,
                    customer_id=appointment.customer_id,
                    technician_id=appointment.technician_id,
                ),
            )

        if current_status == AppointmentStatus.CANCELLED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Không thể xác nhận lịch hẹn đã bị hủy",
            )
        if current_status == AppointmentStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Không thể xác nhận lịch hẹn đã hoàn tất",
            )
        if current_status == AppointmentStatus.IN_PROGRESS.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Không thể xác nhận lịch hẹn đang được thực hiện sửa chữa",
            )

        # 4. Perform update
        prev_status = appointment.status
        appointment.status = AppointmentStatus.CONFIRMED.value
        appointment.updated_at = get_datetime_utc()
        session.add(appointment)

        history = RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status=prev_status,
            new_status=AppointmentStatus.CONFIRMED.value,
            note="Xác nhận lịch hẹn",
            changed_by_user_id=current_user.id,
        )
        session.add(history)

        session.commit()
        session.refresh(appointment)

        return AppointmentConfirmResponse(
            success=True,
            message="Xác nhận lịch hẹn thành công",
            data=AppointmentConfirmData(
                id=appointment.id,
                appointment_number=appointment.appointment_number,
                status=appointment.status,
                appointment_date=appointment.appointment_date,
                customer_id=appointment.customer_id,
                technician_id=appointment.technician_id,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Lỗi hệ thống khi xác nhận lịch hẹn {appointment_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống khi xác nhận lịch hẹn",
        ) from e


def cancel_appointment(
    session: Session,
    appointment_id: uuid.UUID,
    data: AppointmentCancelRequest,
    current_user: User,
) -> AppointmentCancelResponse:
    """API: Hủy lịch hẹn.

    Quy tắc nghiệp vụ:
    1. Kiểm tra tồn tại lịch hẹn (404 Not Found).
    2. Kiểm tra quyền của người gọi (403 Forbidden).
    3. Không cho hủy lịch đã hoàn tất (COMPLETED) hoặc đã hủy (CANCELLED) hoặc đang xử lý (IN_PROGRESS) -> 409 Conflict.
    4. Cập nhật trạng thái sang CANCELLED, lưu lý do hủy cancellation_reason.
    5. Lưu audit log vào RepairStatusHistory với changed_by_user_id và ghi chú hủy.
    6. Slot tự động được giải phóng cho kỹ thuật viên nhờ bộ lọc Appointment.status != 'CANCELLED'.
    7. Không xóa vật lý bản ghi.
    """
    try:
        # 1. Lock appointment row
        appointment = session.exec(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
        ).first()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy lịch hẹn",
            )

        # 2. Check authorization
        check_can_cancel(user=current_user, appointment=appointment, session=session)

        # 3. Status checks
        current_status = (appointment.status or "").upper()
        if current_status == AppointmentStatus.CANCELLED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Lịch hẹn đã bị hủy trước đó",
            )
        if current_status == AppointmentStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Không thể hủy lịch hẹn đã hoàn tất",
            )
        if current_status == AppointmentStatus.IN_PROGRESS.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Không thể hủy lịch hẹn đang được thực hiện sửa chữa",
            )

        # 4. Perform cancellation update
        prev_status = appointment.status
        appointment.status = AppointmentStatus.CANCELLED.value
        appointment.cancellation_reason = data.reason
        if data.note:
            appointment.customer_notes = (
                f"{appointment.customer_notes}\n[Hủy lịch]: {data.note}"
                if appointment.customer_notes
                else f"[Hủy lịch]: {data.note}"
            )
        appointment.updated_at = get_datetime_utc()
        session.add(appointment)

        # Audit history
        audit_note = f"Lý do hủy: {data.reason}"
        if data.note:
            audit_note += f" | Ghi chú: {data.note}"

        history = RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status=prev_status,
            new_status=AppointmentStatus.CANCELLED.value,
            note=audit_note,
            changed_by_user_id=current_user.id,
        )
        session.add(history)

        session.commit()
        session.refresh(appointment)

        return AppointmentCancelResponse(
            success=True,
            message="Hủy lịch hẹn thành công",
            data=AppointmentCancelData(
                id=appointment.id,
                appointment_number=appointment.appointment_number,
                status=appointment.status,
                cancellation_reason=appointment.cancellation_reason,
                customer_notes=appointment.customer_notes,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Lỗi hệ thống khi hủy lịch hẹn {appointment_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống khi hủy lịch hẹn",
        ) from e
