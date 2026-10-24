from fastapi import HTTPException, status
from sqlmodel import Session, col, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    AppointmentService,
    AppointmentServiceItemDetail,
    AppointmentStatus,
    Customer,
    Device,
    DeviceIntakeCreate,
    DeviceIntakeDetail,
    RepairStatusHistory,
    Service,
    Technician,
    User,
    get_datetime_utc,
)
from app.services import slot_service

logger = get_logger("app.services.intake_service")


def _build_intake_detail(
    session: Session,
    appointment: Appointment,
    physical_condition: str,
    fault_description: str,
    accessories_received: str | None,
) -> DeviceIntakeDetail:
    """Helper chuyển đổi Appointment thành DeviceIntakeDetail."""
    customer = session.get(Customer, appointment.customer_id)
    device = session.get(Device, appointment.device_id)
    tech = (
        session.get(Technician, appointment.technician_id)
        if appointment.technician_id
        else None
    )

    # Lấy thông tin các dịch vụ liên kết
    appt_services = session.exec(
        select(AppointmentService).where(
            AppointmentService.appointment_id == appointment.id
        )
    ).all()

    services_items: list[AppointmentServiceItemDetail] = []
    for item in appt_services:
        svc = session.get(Service, item.service_id)
        services_items.append(
            AppointmentServiceItemDetail(
                service_id=item.service_id,
                service_name=svc.name if svc else "Dịch vụ sửa chữa",
                price_at_booking=item.price_at_booking,
                quantity=item.quantity,
                notes=item.notes,
            )
        )

    return DeviceIntakeDetail(
        id=appointment.id,
        appointment_number=appointment.appointment_number,
        status=appointment.status,
        appointment_date=appointment.appointment_date,
        customer_id=appointment.customer_id,
        customer_name=customer.full_name if customer else "Khách hàng",
        customer_phone=customer.phone_number if customer else "",
        device_id=appointment.device_id,
        device_brand=device.brand if device else "Không rõ",
        device_model=device.model if device else "Không rõ",
        device_imei=device.imei if device else None,
        device_color=device.color if device else None,
        physical_condition=physical_condition,
        fault_description=fault_description,
        accessories_received=accessories_received,
        technician_id=appointment.technician_id,
        technician_name=tech.full_name if tech else None,
        estimated_completion_date=appointment.estimated_completion_date,
        total_amount=appointment.total_amount,
        services=services_items,
        created_at=appointment.created_at,
    )


def _handle_existing_appointment_intake(
    session: Session,
    intake_in: DeviceIntakeCreate,
    current_user: User,
) -> DeviceIntakeDetail:
    """Xử lý tiếp nhận thiết bị từ lịch hẹn đã đặt trước."""
    assert intake_in.appointment_id is not None
    now = get_datetime_utc()
    physical_condition = intake_in.physical_condition.strip()
    fault_description = intake_in.fault_description.strip()
    accessories_received = (
        intake_in.accessories_received.strip()
        if intake_in.accessories_received and intake_in.accessories_received.strip()
        else None
    )

    appointment = session.get(Appointment, intake_in.appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy lịch hẹn với ID {intake_in.appointment_id}",
        )

    # Kiểm tra trạng thái lịch hẹn hợp lệ để tiếp nhận
    if appointment.status == AppointmentStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lịch hẹn đã bị hủy, không thể lập phiếu tiếp nhận thiết bị",
        )
    if appointment.status == AppointmentStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lịch hẹn đã hoàn tất, không thể lập phiếu tiếp nhận thiết bị",
        )
    if appointment.status == AppointmentStatus.IN_PROGRESS.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lịch hẹn {appointment.appointment_number} đã được tiếp nhận và đang trong quá trình sửa chữa",
        )

    customer = session.get(Customer, appointment.customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin khách hàng liên kết với lịch hẹn",
        )

    device = session.get(Device, appointment.device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin thiết bị liên kết với lịch hẹn",
        )

    # Cập nhật thông tin chi tiết thiết bị nếu có bổ sung
    if intake_in.brand and intake_in.brand.strip():
        device.brand = intake_in.brand.strip()
    if intake_in.model and intake_in.model.strip():
        device.model = intake_in.model.strip()
    if intake_in.color and intake_in.color.strip():
        device.color = intake_in.color.strip()
    if intake_in.imei and intake_in.imei.strip():
        device.imei = intake_in.imei.strip()
    if intake_in.serial_number and intake_in.serial_number.strip():
        device.serial_number = intake_in.serial_number.strip()
    if accessories_received:
        device.notes = f"Phụ kiện bàn giao: {accessories_received}"
    device.updated_at = now
    session.add(device)

    # Kiểm tra kỹ thuật viên phụ trách nếu có truyền
    if intake_in.technician_id:
        tech = session.get(Technician, intake_in.technician_id)
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy kỹ thuật viên với ID {intake_in.technician_id}",
            )
        if not tech.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kỹ thuật viên này hiện không còn hoạt động",
            )
        appointment.technician_id = tech.id

    # Cập nhật dịch vụ nếu có truyền bổ sung
    if intake_in.service_ids:
        existing_svc_ids = set(
            session.exec(
                select(AppointmentService.service_id).where(
                    AppointmentService.appointment_id == appointment.id
                )
            ).all()
        )
        added_amount = 0.0
        for s_id in intake_in.service_ids:
            if s_id not in existing_svc_ids:
                svc = session.get(Service, s_id)
                if not svc:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Không tìm thấy dịch vụ sửa chữa với ID {s_id}",
                    )
                if not svc.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Dịch vụ '{svc.name}' hiện không hoạt động",
                    )
                appt_svc = AppointmentService(
                    appointment_id=appointment.id,
                    service_id=svc.id,
                    price_at_booking=svc.base_price,
                    quantity=1,
                    notes="Bổ sung khi tiếp nhận máy tại quầy",
                )
                session.add(appt_svc)
                added_amount += svc.base_price
        appointment.total_amount += added_amount

    # Cập nhật chẩn đoán tiếp nhận và trạng thái
    old_status = appointment.status
    new_status = intake_in.initial_status.value
    appointment.status = new_status

    diagnosis_parts = [f"Tình trạng ngoại quan: {physical_condition}"]
    if accessories_received:
        diagnosis_parts.append(f"Phụ kiện kèm theo: {accessories_received}")
    appointment.technician_diagnosis = ". ".join(diagnosis_parts)
    appointment.customer_notes = fault_description

    if intake_in.estimated_completion_date:
        appointment.estimated_completion_date = intake_in.estimated_completion_date
    appointment.updated_at = now
    session.add(appointment)

    # Ghi nhận lịch sử trạng thái (Audit Trail)
    audit_note = (
        f"Tiếp nhận thiết bị sửa chữa theo lịch hẹn {appointment.appointment_number}. "
        f"Ngoại quan: {physical_condition}. "
        f"Phụ kiện: {accessories_received or 'Không có'}"
    )
    status_history = RepairStatusHistory(
        appointment_id=appointment.id,
        previous_status=old_status,
        new_status=new_status,
        note=audit_note,
        changed_by_user_id=current_user.id,
    )
    session.add(status_history)

    session.commit()
    session.refresh(appointment)

    logger.info(
        f"Tiếp nhận thiết bị thành công cho lịch hẹn {appointment.appointment_number}"
    )
    return _build_intake_detail(
        session=session,
        appointment=appointment,
        physical_condition=physical_condition,
        fault_description=fault_description,
        accessories_received=accessories_received,
    )


def _handle_walkin_intake(
    session: Session,
    intake_in: DeviceIntakeCreate,
    current_user: User,
) -> DeviceIntakeDetail:
    """Xử lý tiếp nhận thiết bị trực tiếp tại quầy cho khách vãng lai."""
    now = get_datetime_utc()
    physical_condition = intake_in.physical_condition.strip()
    fault_description = intake_in.fault_description.strip()
    accessories_received = (
        intake_in.accessories_received.strip()
        if intake_in.accessories_received and intake_in.accessories_received.strip()
        else None
    )

    # 1. Xác định hoặc tạo khách hàng
    walkin_customer: Customer | None = None
    if intake_in.customer_id:
        walkin_customer = session.get(Customer, intake_in.customer_id)
        if not walkin_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy khách hàng với ID {intake_in.customer_id}",
            )
    else:
        assert intake_in.customer_name is not None
        assert intake_in.customer_phone is not None
        phone_clean = intake_in.customer_phone.strip()
        name_clean = intake_in.customer_name.strip()

        # Tìm xem số điện thoại đã tồn tại trong hệ thống chưa để liên kết
        existing_cust = session.exec(
            select(Customer).where(Customer.phone_number == phone_clean)
        ).first()

        if existing_cust:
            walkin_customer = existing_cust
            if intake_in.customer_email and not walkin_customer.email:
                walkin_customer.email = intake_in.customer_email.strip()
            if intake_in.customer_address and not walkin_customer.address:
                walkin_customer.address = intake_in.customer_address.strip()
            walkin_customer.updated_at = now
            session.add(walkin_customer)
        else:
            walkin_customer = Customer(
                full_name=name_clean,
                phone_number=phone_clean,
                email=(
                    intake_in.customer_email.strip()
                    if intake_in.customer_email
                    else None
                ),
                address=(
                    intake_in.customer_address.strip()
                    if intake_in.customer_address
                    else None
                ),
            )
            session.add(walkin_customer)
            session.flush()

    assert walkin_customer is not None

    # 2. Xác định hoặc tạo thiết bị
    walkin_device: Device | None = None
    if intake_in.device_id:
        walkin_device = session.get(Device, intake_in.device_id)
        if not walkin_device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy thiết bị với ID {intake_in.device_id}",
            )
        if walkin_device.customer_id != walkin_customer.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thiết bị được chỉ định không thuộc về khách hàng này",
            )
        # Kiểm tra chống trùng: thiết bị này có đang sửa dở dang không
        active_repair = session.exec(
            select(Appointment).where(
                Appointment.device_id == walkin_device.id,
                col(Appointment.status).in_(
                    [
                        AppointmentStatus.PENDING.value,
                        AppointmentStatus.CONFIRMED.value,
                        AppointmentStatus.IN_PROGRESS.value,
                    ]
                ),
            )
        ).first()
        if active_repair:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Thiết bị đang có phiếu sửa chữa chưa hoàn tất ({active_repair.appointment_number}), không thể tiếp nhận thêm",
            )
    else:
        assert intake_in.brand is not None
        assert intake_in.model is not None
        brand_clean = intake_in.brand.strip()
        model_clean = intake_in.model.strip()
        imei_clean = (
            intake_in.imei.strip()
            if intake_in.imei and intake_in.imei.strip()
            else None
        )
        serial_clean = (
            intake_in.serial_number.strip()
            if intake_in.serial_number and intake_in.serial_number.strip()
            else None
        )

        # Chống trùng: kiểm tra IMEI hoặc SerialNumber xem có thiết bị đang sửa dở dang không
        existing_device: Device | None = None
        if imei_clean:
            existing_device = session.exec(
                select(Device).where(col(Device.imei) == imei_clean)
            ).first()
        if not existing_device and serial_clean:
            existing_device = session.exec(
                select(Device).where(col(Device.serial_number) == serial_clean)
            ).first()

        if existing_device:
            active_repair = session.exec(
                select(Appointment).where(
                    Appointment.device_id == existing_device.id,
                    col(Appointment.status).in_(
                        [
                            AppointmentStatus.PENDING.value,
                            AppointmentStatus.CONFIRMED.value,
                            AppointmentStatus.IN_PROGRESS.value,
                        ]
                    ),
                )
            ).first()
            if active_repair:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Thiết bị có số IMEI/Serial này đang có phiếu sửa chữa dở dang ({active_repair.appointment_number})",
                )

        walkin_device = Device(
            customer_id=walkin_customer.id,
            brand=brand_clean,
            model=model_clean,
            device_type=intake_in.device_type.strip(),
            serial_number=serial_clean,
            imei=imei_clean,
            color=(
                intake_in.color.strip()
                if intake_in.color and intake_in.color.strip()
                else None
            ),
            notes=(
                f"Phụ kiện bàn giao: {accessories_received}"
                if accessories_received
                else None
            ),
        )
        session.add(walkin_device)
        session.flush()

    assert walkin_device is not None

    # 3. Kiểm tra kỹ thuật viên (nếu có)
    technician: Technician | None = None
    if intake_in.technician_id:
        technician = session.get(Technician, intake_in.technician_id)
        if not technician:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy kỹ thuật viên với ID {intake_in.technician_id}",
            )
        if not technician.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kỹ thuật viên này hiện không còn hoạt động",
            )

    # 4. Kiểm tra danh sách dịch vụ và tính tổng tiền
    total_amount = 0.0
    selected_services: list[Service] = []
    if intake_in.service_ids:
        for s_id in intake_in.service_ids:
            svc = session.get(Service, s_id)
            if not svc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Không tìm thấy dịch vụ sửa chữa với ID {s_id}",
                )
            if not svc.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dịch vụ '{svc.name}' hiện không hoạt động",
                )
            selected_services.append(svc)
            total_amount += svc.base_price

    # 5. Sinh mã phiếu tiếp nhận và khởi tạo lịch hẹn/đơn sửa chữa
    appointment_code = slot_service.generate_appointment_code(session, now.date())

    diagnosis_parts = [f"Tình trạng ngoại quan: {physical_condition}"]
    if accessories_received:
        diagnosis_parts.append(f"Phụ kiện kèm theo: {accessories_received}")

    new_status = intake_in.initial_status.value
    appointment = Appointment(
        appointment_number=appointment_code,
        appointment_date=now,
        status=new_status,
        customer_id=walkin_customer.id,
        device_id=walkin_device.id,
        technician_id=technician.id if technician else None,
        customer_notes=fault_description,
        technician_diagnosis=". ".join(diagnosis_parts),
        estimated_completion_date=intake_in.estimated_completion_date,
        total_amount=total_amount,
    )
    session.add(appointment)
    session.flush()

    # 6. Ghi nhận dịch vụ vào AppointmentService
    for svc in selected_services:
        appt_svc = AppointmentService(
            appointment_id=appointment.id,
            service_id=svc.id,
            price_at_booking=svc.base_price,
            quantity=1,
            notes="Dịch vụ tiếp nhận tại quầy",
        )
        session.add(appt_svc)

    # 7. Ghi nhận nhật ký trạng thái (Audit Trail)
    audit_note = (
        f"Tạo phiếu tiếp nhận thiết bị trực tiếp tại quầy ({appointment.appointment_number}). "
        f"Ngoại quan: {physical_condition}. "
        f"Phụ kiện: {accessories_received or 'Không có'}"
    )
    status_history = RepairStatusHistory(
        appointment_id=appointment.id,
        previous_status=None,
        new_status=new_status,
        note=audit_note,
        changed_by_user_id=current_user.id,
    )
    session.add(status_history)

    session.commit()
    session.refresh(appointment)

    logger.info(
        f"Tạo phiếu tiếp nhận trực tiếp thành công với mã {appointment.appointment_number}"
    )
    return _build_intake_detail(
        session=session,
        appointment=appointment,
        physical_condition=physical_condition,
        fault_description=fault_description,
        accessories_received=accessories_received,
    )


def create_device_intake(
    session: Session,
    intake_in: DeviceIntakeCreate,
    current_user: User,
) -> DeviceIntakeDetail:
    """
    Tạo hoặc cập nhật phiếu tiếp nhận thiết bị sửa chữa:
    - Hỗ trợ tiếp nhận theo lịch hẹn có sẵn hoặc tiếp nhận trực tiếp tại quầy (walk-in).
    - Ghi nhận thông tin thiết bị, tình trạng ngoại quan, mô tả lỗi và phụ kiện bàn giao.
    - Tự động sinh mã phiếu APPT-YYYYMMDD-XXXX (nếu walk-in).
    - Khởi tạo trạng thái CONFIRMED hoặc IN_PROGRESS.
    - Lưu nhật ký kiểm toán vào RepairStatusHistory.
    - Thực hiện bằng transaction an toàn.
    """
    logger.info(
        f"Bắt đầu lập phiếu tiếp nhận thiết bị sửa chữa bởi user={current_user.id} ({current_user.email})"
    )

    try:
        if intake_in.appointment_id:
            return _handle_existing_appointment_intake(
                session=session,
                intake_in=intake_in,
                current_user=current_user,
            )
        return _handle_walkin_intake(
            session=session,
            intake_in=intake_in,
            current_user=current_user,
        )
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        logger.error(
            f"Lỗi không xác định khi tạo phiếu tiếp nhận thiết bị: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra lỗi trong quá trình tạo phiếu tiếp nhận thiết bị. Vui lòng thử lại sau.",
        ) from exc
