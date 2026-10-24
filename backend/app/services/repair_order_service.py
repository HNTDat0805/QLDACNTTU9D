import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    AppointmentStatus,
    AssignTechnicianData,
    AssignTechnicianRequest,
    RepairStatusHistory,
    RepairStatusUpdateData,
    RepairStatusUpdateRequest,
    Technician,
    TechnicianSchedule,
    User,
    get_datetime_utc,
)

logger = get_logger("app.services.repair_order_service")


def update_repair_status(
    session: Session,
    repair_order_id: uuid.UUID,
    data: RepairStatusUpdateRequest,
    current_user: User,
) -> RepairStatusUpdateData:
    """
    Cập nhật trạng thái xử lý của phiếu sửa chữa và ghi nhận lịch sử thay đổi:
    - Sử dụng with_for_update() khóa dòng để tránh xung đột cập nhật đồng thời.
    - Kiểm tra phiếu sửa chữa tồn tại (404 Not Found).
    - Kiểm tra quy tắc chuyển trạng thái hợp lệ theo chu trình sửa chữa.
    - Chặn cập nhật khi phiếu sửa chữa đã kết thúc (COMPLETED, CANCELLED -> 409 Conflict).
    - Chặn chuyển sang chính trạng thái hiện tại (400 Bad Request).
    - Tự động cập nhật actual_completion_date khi COMPLETED.
    - Tự động cập nhật cancellation_reason khi CANCELLED.
    - Ghi nhận lịch sử chuyển trạng thái vào RepairStatusHistory trong cùng transaction.
    """
    logger.info(
        f"Bắt đầu cập nhật trạng thái phiếu sửa chữa {repair_order_id} sang {data.status} bởi user={current_user.id}"
    )

    now = get_datetime_utc()

    try:
        appointment = session.exec(
            select(Appointment)
            .where(Appointment.id == repair_order_id)
            .with_for_update()
        ).first()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy phiếu sửa chữa với ID: {repair_order_id}",
            )

        old_status = (appointment.status or "").upper()
        new_status = data.status.value.upper()

        # Không cho phép cập nhật phiếu đã kết thúc
        if old_status in ("COMPLETED", "CANCELLED"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Không thể cập nhật phiếu sửa chữa đã kết thúc (trạng thái hiện tại: {old_status})",
            )

        # Không cho phép chuyển sang chính trạng thái hiện tại
        if old_status == new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phiếu sửa chữa đã ở trạng thái '{new_status}'",
            )

        # Ràng buộc quy trình: không thể chuyển từ PENDING thẳng sang COMPLETED
        if (
            old_status == AppointmentStatus.PENDING.value
            and new_status == AppointmentStatus.COMPLETED.value
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phiếu sửa chữa cần được tiếp nhận và xử lý (CONFIRMED/IN_PROGRESS) trước khi hoàn tất",
            )

        # Cập nhật các trường đặc thù theo trạng thái đích
        if new_status == AppointmentStatus.COMPLETED.value:
            appointment.actual_completion_date = now

        if new_status == AppointmentStatus.CANCELLED.value:
            reason = data.cancellation_reason or data.note or "Hủy bởi nhân viên"
            appointment.cancellation_reason = reason.strip()

        if data.technician_diagnosis and data.technician_diagnosis.strip():
            appointment.technician_diagnosis = data.technician_diagnosis.strip()

        # Ghi nhận lịch sử trạng thái (Audit Trail)
        note_text = (
            data.note.strip()
            if data.note and data.note.strip()
            else f"Chuyển trạng thái từ {old_status} sang {new_status}"
        )
        history = RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status=old_status,
            new_status=new_status,
            note=note_text,
            changed_by_user_id=current_user.id,
            created_at=now,
        )
        session.add(history)

        appointment.status = new_status
        appointment.updated_at = now
        session.add(appointment)

        session.commit()
        session.refresh(appointment)
        session.refresh(history)

        logger.info(
            f"Cập nhật thành công trạng thái phiếu {appointment.appointment_number}: {old_status} -> {new_status}"
        )

        return RepairStatusUpdateData(
            id=appointment.id,
            appointment_number=appointment.appointment_number,
            previous_status=old_status,
            current_status=new_status,
            note=history.note,
            technician_diagnosis=appointment.technician_diagnosis,
            actual_completion_date=appointment.actual_completion_date,
            updated_at=appointment.updated_at,
            history_id=history.id,
        )

    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        logger.error(
            f"Lỗi không xác định khi cập nhật trạng thái phiếu sửa chữa: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra lỗi trong quá trình cập nhật trạng thái sửa chữa. Vui lòng thử lại sau.",
        ) from exc


def assign_technician_to_repair(
    session: Session,
    repair_order_id: uuid.UUID,
    data: AssignTechnicianRequest,
    current_user: User,
) -> AssignTechnicianData:
    """
    Phân công hoặc thay đổi kỹ thuật viên phụ trách phiếu sửa chữa:
    - Sử dụng with_for_update() khóa dòng để tránh xung đột phân công đồng thời.
    - Kiểm tra phiếu sửa chữa tồn tại (404 Not Found).
    - Kiểm tra trạng thái phiếu sửa chữa (chặn khi COMPLETED, CANCELLED -> 409 Conflict).
    - Kiểm tra kỹ thuật viên tồn tại (404 Not Found).
    - Kiểm tra kỹ thuật viên đang hoạt động (400 Bad Request nếu is_active=False).
    - Kiểm tra lịch làm việc nếu kỹ thuật viên đăng ký nghỉ phép (OFF) trong ngày (400 Bad Request).
    - Cập nhật technician_id và ghi nhận lịch sử vào RepairStatusHistory trong cùng transaction.
    """
    logger.info(
        f"Bắt đầu phân công kỹ thuật viên {data.technician_id} cho phiếu sửa chữa {repair_order_id} bởi user={current_user.id}"
    )

    now = get_datetime_utc()

    try:
        appointment = session.exec(
            select(Appointment)
            .where(Appointment.id == repair_order_id)
            .with_for_update()
        ).first()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy phiếu sửa chữa với ID: {repair_order_id}",
            )

        if appointment.status in ("COMPLETED", "CANCELLED"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Không thể phân công kỹ thuật viên cho phiếu sửa chữa đã kết thúc ({appointment.status})",
            )

        tech = session.get(Technician, data.technician_id)
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy kỹ thuật viên với ID: {data.technician_id}",
            )

        if not tech.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Kỹ thuật viên '{tech.full_name}' hiện không hoạt động hoặc đã nghỉ việc",
            )

        # Kiểm tra lịch làm việc của kỹ thuật viên trong ngày hôm nay nếu có đăng ký OFF
        today = now.date()
        schedule_off = session.exec(
            select(TechnicianSchedule).where(
                TechnicianSchedule.technician_id == tech.id,
                TechnicianSchedule.work_date == today,
                TechnicianSchedule.status == "OFF",
            )
        ).first()

        if schedule_off:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Kỹ thuật viên '{tech.full_name}' đã đăng ký nghỉ (OFF) trong ngày hôm nay, không thể nhận việc",
            )

        old_tech_id = appointment.technician_id
        old_tech = session.get(Technician, old_tech_id) if old_tech_id else None

        appointment.technician_id = tech.id
        appointment.updated_at = now
        session.add(appointment)

        # Ghi nhận lịch sử phân công vào RepairStatusHistory
        if old_tech and old_tech.id != tech.id:
            audit_note = f"Thay đổi kỹ thuật viên phụ trách từ {old_tech.full_name} sang {tech.full_name}"
        else:
            audit_note = f"Phân công kỹ thuật viên {tech.full_name} phụ trách sửa chữa"

        if data.note and data.note.strip():
            audit_note += f". Ghi chú: {data.note.strip()}"

        history = RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status=appointment.status,
            new_status=appointment.status,
            note=audit_note,
            changed_by_user_id=current_user.id,
            created_at=now,
        )
        session.add(history)

        session.commit()
        session.refresh(appointment)

        logger.info(
            f"Phân công thành công kỹ thuật viên {tech.full_name} cho phiếu {appointment.appointment_number}"
        )

        return AssignTechnicianData(
            id=appointment.id,
            appointment_number=appointment.appointment_number,
            technician_id=tech.id,
            technician_name=tech.full_name,
            technician_phone=tech.phone_number,
            specialization=tech.specialization,
            status=appointment.status,
            assigned_at=now,
        )

    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        logger.error(
            f"Lỗi không xác định khi phân công kỹ thuật viên: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra lỗi trong quá trình phân công kỹ thuật viên. Vui lòng thử lại sau.",
        ) from exc
