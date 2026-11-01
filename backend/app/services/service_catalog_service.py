import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlmodel import Session, col, func, select

from app.core.logging import get_logger
from app.models import (
    Service,
    ServiceCreate,
    ServicePublic,
    ServiceUpdate,
    SystemLog,
    User,
    get_datetime_utc,
)

logger = get_logger("app.services.service_catalog_service")


def get_services(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    is_active: bool | None = None,
    q: str | None = None,
) -> tuple[list[ServicePublic], int]:
    """
    Truy vấn danh mục dịch vụ có phân trang và bộ lọc:
    - is_active: True (chỉ lấy dịch vụ đang hiển thị cho khách hàng), False (dịch vụ ẩn), None (tất cả).
    - q: tìm kiếm theo tên hoặc mã dịch vụ.
    """
    statement = select(Service)
    count_statement = select(func.count()).select_from(Service)

    conditions: list[Any] = []
    if is_active is not None:
        conditions.append(col(Service.is_active) == is_active)
    if q and q.strip():
        term = q.strip()
        conditions.append(
            or_(
                col(Service.name).ilike(f"%{term}%"),
                col(Service.code).ilike(f"%{term}%"),
                col(Service.description).ilike(f"%{term}%"),
            )
        )

    for cond in conditions:
        statement = statement.where(cond)
        count_statement = count_statement.where(cond)

    count = session.exec(count_statement).one()
    services = session.exec(
        statement.order_by(col(Service.created_at).desc()).offset(skip).limit(limit)
    ).all()

    return [ServicePublic.model_validate(s) for s in services], count


def get_service_by_id(session: Session, service_id: uuid.UUID) -> ServicePublic:
    """Xem chi tiết dịch vụ sửa chữa theo ID."""
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy dịch vụ với ID {service_id}",
        )
    return ServicePublic.model_validate(service)


def create_service(
    session: Session,
    data: ServiceCreate,
    current_user: User,
) -> ServicePublic:
    """
    Tạo mới dịch vụ sửa chữa (Yêu cầu quyền Admin/Manager):
    - Kiểm tra tính hợp lệ của mã dịch vụ và tên dịch vụ.
    - Không cho phép mã dịch vụ bị trùng (409 Conflict).
    - Không cho phép tên dịch vụ bị trùng (409 Conflict).
    - Kiểm tra giá dịch vụ >= 0 và thời gian dự kiến > 0.
    - Lưu vào PostgreSQL và ghi nhật ký kiểm toán SystemLog.
    """
    if data.code:
        normalized_code = data.code.strip().upper()
        # Kiểm tra mã dịch vụ duy nhất
        existing_code = session.exec(
            select(Service).where(col(Service.code) == normalized_code)
        ).first()
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Mã dịch vụ '{normalized_code}' đã tồn tại trong hệ thống",
            )
    else:
        normalized_code = f"SVC-{uuid.uuid4().hex[:8].upper()}"
    normalized_name = data.name.strip()

    # Kiểm tra tên dịch vụ duy nhất
    existing_name = session.exec(
        select(Service).where(col(Service.name) == normalized_name)
    ).first()
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tên dịch vụ '{normalized_name}' đã tồn tại trong hệ thống",
        )

    now = get_datetime_utc()
    service = Service(
        id=uuid.uuid4(),
        code=normalized_code,
        name=normalized_name,
        description=data.description.strip() if data.description else None,
        base_price=float(data.base_price),
        estimated_duration_minutes=int(data.estimated_duration_minutes),
        is_active=data.is_active,
        created_at=now,
        updated_at=now,
    )
    session.add(service)

    # Ghi nhận nhật ký kiểm toán hệ thống
    audit_log = SystemLog(
        action="CREATE_SERVICE",
        entity_name="service",
        entity_id=str(service.id),
        details=f"Tạo dịch vụ '{service.name}' (Mã: {service.code}, Giá: {service.base_price:,.0f}đ) bởi user {current_user.email}",
        user_id=current_user.id,
        created_at=now,
    )
    session.add(audit_log)

    session.commit()
    session.refresh(service)

    logger.info(
        f"Đã tạo dịch vụ '{service.name}' (Mã: {service.code}, ID: {service.id}) bởi user={current_user.id}"
    )
    return ServicePublic.model_validate(service)


def update_service(
    session: Session,
    service_id: uuid.UUID,
    data: ServiceUpdate,
    current_user: User,
) -> ServicePublic:
    """
    Cập nhật dịch vụ sửa chữa (Yêu cầu quyền Admin/Manager):
    - Kiểm tra dịch vụ có tồn tại hay không (404 Not Found).
    - Kiểm tra tính hợp lệ dữ liệu.
    - Không cho phép trùng tên với dịch vụ khác (409 Conflict).
    - Không tự ý thay đổi mã định danh của dịch vụ (code được giữ nguyên).
    - Cập nhật thời gian updated_at và ghi nhận nhật ký kiểm toán.
    """
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy dịch vụ với ID {service_id}",
        )

    update_dict = data.model_dump(exclude_unset=True)

    # Không cho phép thay đổi mã định danh của dịch vụ
    update_dict.pop("code", None)

    # Kiểm tra tên mới không trùng với dịch vụ khác
    if "name" in update_dict and update_dict["name"]:
        new_name = update_dict["name"].strip()
        existing_name = session.exec(
            select(Service).where(
                col(Service.name) == new_name,
                col(Service.id) != service_id,
            )
        ).first()
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tên dịch vụ '{new_name}' đã được sử dụng bởi một dịch vụ khác",
            )
        update_dict["name"] = new_name

    now = get_datetime_utc()
    service.sqlmodel_update(update_dict)
    service.updated_at = now
    session.add(service)

    # Ghi nhận nhật ký kiểm toán hệ thống
    audit_log = SystemLog(
        action="UPDATE_SERVICE",
        entity_name="service",
        entity_id=str(service.id),
        details=f"Cập nhật thông tin dịch vụ '{service.name}' (Mã: {service.code}) bởi user {current_user.email}",
        user_id=current_user.id,
        created_at=now,
    )
    session.add(audit_log)

    session.commit()
    session.refresh(service)

    logger.info(
        f"Đã cập nhật dịch vụ ID={service.id} (Mã: {service.code}) bởi user={current_user.id}"
    )
    return ServicePublic.model_validate(service)


def hide_service(
    session: Session,
    service_id: uuid.UUID,
    current_user: User,
) -> ServicePublic:
    """
    Ẩn dịch vụ sửa chữa (Soft Delete / Ngừng kinh doanh):
    - Kiểm tra dịch vụ có tồn tại hay không (404 Not Found).
    - Không xóa dữ liệu vật lý khỏi database để bảo toàn toàn vẹn tham chiếu với các lịch hẹn cũ.
    - Cập nhật is_active = False.
    - Dịch vụ bị ẩn sẽ không còn xuất hiện trong danh sách dịch vụ dành cho khách hàng.
    - Ghi nhận nhật ký kiểm toán SystemLog.
    """
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy dịch vụ với ID {service_id}",
        )

    now = get_datetime_utc()
    service.is_active = False
    service.updated_at = now
    session.add(service)

    # Ghi nhận nhật ký kiểm toán hệ thống
    audit_log = SystemLog(
        action="HIDE_SERVICE",
        entity_name="service",
        entity_id=str(service.id),
        details=f"Ẩn dịch vụ '{service.name}' (Mã: {service.code}) khỏi danh mục hiển thị bởi user {current_user.email}",
        user_id=current_user.id,
        created_at=now,
    )
    session.add(audit_log)

    session.commit()
    session.refresh(service)

    logger.info(
        f"Đã ẩn thành công dịch vụ ID={service.id} (Mã: {service.code}) bởi user={current_user.id}"
    )
    return ServicePublic.model_validate(service)
