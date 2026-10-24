import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlmodel import Session, col, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    Message,
    Technician,
    TechnicianCreate,
    TechnicianPublic,
    TechnicianSchedule,
    TechniciansPublic,
    TechnicianUpdate,
    User,
    get_datetime_utc,
)

logger = get_logger("app.services.technician_service")


def get_technicians(
    session: Session,
    skip: int = 0,
    limit: int = 20,
    is_active: bool | None = None,
    specialization: str | None = None,
    q: str | None = None,
) -> TechniciansPublic:
    """Lấy danh sách kỹ thuật viên hỗ trợ lọc theo trạng thái, chuyên môn và tìm kiếm."""
    query = select(Technician)
    count_query = select(func.count()).select_from(Technician)

    if is_active is not None:
        query = query.where(Technician.is_active == is_active)
        count_query = count_query.where(Technician.is_active == is_active)

    if specialization and specialization.strip():
        spec_pattern = f"%{specialization.strip()}%"
        query = query.where(col(Technician.specialization).ilike(spec_pattern))
        count_query = count_query.where(
            col(Technician.specialization).ilike(spec_pattern)
        )

    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        filter_clause = or_(
            col(Technician.full_name).ilike(search_pattern),
            col(Technician.phone_number).ilike(search_pattern),
            col(Technician.specialization).ilike(search_pattern),
        )
        query = query.where(filter_clause)
        count_query = count_query.where(filter_clause)

    total_count = session.exec(count_query).one()
    items = session.exec(
        query.order_by(col(Technician.created_at).desc()).offset(skip).limit(limit)
    ).all()

    return TechniciansPublic(
        data=[TechnicianPublic.model_validate(t) for t in items],
        count=total_count,
    )


def create_technician(
    session: Session,
    data: TechnicianCreate,
) -> TechnicianPublic:
    """Tạo mới kỹ thuật viên với kiểm tra số điện thoại và tài khoản người dùng liên kết."""
    full_name = data.full_name.strip()
    phone = data.phone_number.strip() if data.phone_number else None

    if phone:
        existing_phone = session.exec(
            select(Technician).where(Technician.phone_number == phone)
        ).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Số điện thoại kỹ thuật viên đã tồn tại",
            )

    if data.user_id:
        user = session.get(User, data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tài khoản người dùng liên kết không tồn tại",
            )
        existing_tech_user = session.exec(
            select(Technician).where(Technician.user_id == data.user_id)
        ).first()
        if existing_tech_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tài khoản người dùng đã được liên kết với một kỹ thuật viên khác",
            )

    tech = Technician(
        full_name=full_name,
        phone_number=phone,
        specialization=data.specialization.strip() if data.specialization else None,
        is_active=data.is_active,
        user_id=data.user_id,
        created_at=get_datetime_utc(),
    )
    session.add(tech)
    session.commit()
    session.refresh(tech)

    return TechnicianPublic.model_validate(tech)


def get_technician_by_id(
    session: Session,
    technician_id: uuid.UUID,
) -> TechnicianPublic:
    """Lấy chi tiết một kỹ thuật viên theo ID."""
    tech = session.get(Technician, technician_id)
    if not tech:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy kỹ thuật viên",
        )
    return TechnicianPublic.model_validate(tech)


def update_technician(
    session: Session,
    technician_id: uuid.UUID,
    data: TechnicianUpdate,
) -> TechnicianPublic:
    """Cập nhật thông tin kỹ thuật viên."""
    tech = session.get(Technician, technician_id)
    if not tech:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy kỹ thuật viên",
        )

    update_dict = data.model_dump(exclude_unset=True)

    if "phone_number" in update_dict and update_dict["phone_number"] is not None:
        new_phone = update_dict["phone_number"].strip()
        if new_phone:
            duplicate = session.exec(
                select(Technician).where(
                    Technician.phone_number == new_phone,
                    Technician.id != technician_id,
                )
            ).first()
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Số điện thoại đã thuộc về một kỹ thuật viên khác",
                )
        update_dict["phone_number"] = new_phone or None

    if "full_name" in update_dict and update_dict["full_name"] is not None:
        update_dict["full_name"] = update_dict["full_name"].strip()

    if "specialization" in update_dict and update_dict["specialization"] is not None:
        update_dict["specialization"] = update_dict["specialization"].strip()

    update_dict["updated_at"] = get_datetime_utc()
    tech.sqlmodel_update(update_dict)
    session.add(tech)
    session.commit()
    session.refresh(tech)

    return TechnicianPublic.model_validate(tech)


def update_technician_status(
    session: Session,
    technician_id: uuid.UUID,
    is_active: bool,
) -> TechnicianPublic:
    """Cập nhật trạng thái hoạt động / nghỉ việc của kỹ thuật viên."""
    tech = session.get(Technician, technician_id)
    if not tech:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy kỹ thuật viên",
        )

    tech.is_active = is_active
    tech.updated_at = get_datetime_utc()
    session.add(tech)
    session.commit()
    session.refresh(tech)

    return TechnicianPublic.model_validate(tech)


def delete_technician(
    session: Session,
    technician_id: uuid.UUID,
) -> Message:
    """Xóa kỹ thuật viên chỉ khi không có lịch hẹn hoặc ca làm việc liên quan."""
    tech = session.get(Technician, technician_id)
    if not tech:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy kỹ thuật viên",
        )

    has_appointments = session.exec(
        select(Appointment.id).where(Appointment.technician_id == technician_id)
    ).first()
    if has_appointments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa kỹ thuật viên đã được liên kết với lịch hẹn sửa chữa. Vui lòng cập nhật is_active = False",
        )

    has_schedules = session.exec(
        select(TechnicianSchedule.id).where(
            TechnicianSchedule.technician_id == technician_id
        )
    ).first()
    if has_schedules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa kỹ thuật viên đã có lịch làm việc trong hệ thống. Vui lòng cập nhật is_active = False",
        )

    session.delete(tech)
    session.commit()
    return Message(message="Kỹ thuật viên đã được xóa thành công")
