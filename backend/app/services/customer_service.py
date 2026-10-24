import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlmodel import Session, col, select

from app.core.logging import get_logger
from app.models import (
    Appointment,
    Customer,
    CustomerCreate,
    CustomerPublic,
    CustomersPublic,
    CustomerUpdate,
    Invoice,
    Message,
    User,
    get_datetime_utc,
)

logger = get_logger("app.services.customer_service")


def get_customers(
    session: Session,
    skip: int = 0,
    limit: int = 20,
    q: str | None = None,
) -> CustomersPublic:
    """Lấy danh sách khách hàng có phân trang và tìm kiếm theo tên, SĐT, email."""
    query = select(Customer)
    count_query = select(func.count()).select_from(Customer)

    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        filter_clause = or_(
            col(Customer.full_name).ilike(search_pattern),
            col(Customer.phone_number).ilike(search_pattern),
            col(Customer.email).ilike(search_pattern),
        )
        query = query.where(filter_clause)
        count_query = count_query.where(filter_clause)

    total_count = session.exec(count_query).one()
    items = session.exec(
        query.order_by(col(Customer.created_at).desc()).offset(skip).limit(limit)
    ).all()

    return CustomersPublic(
        data=[CustomerPublic.model_validate(c) for c in items],
        count=total_count,
    )


def create_customer(
    session: Session,
    data: CustomerCreate,
) -> CustomerPublic:
    """Tạo mới khách hàng sau khi kiểm tra tính hợp lệ và không trùng lặp."""
    full_name = data.full_name.strip()
    phone_number = data.phone_number.strip()

    if len(phone_number) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số điện thoại phải có ít nhất 8 chữ số",
        )

    # Kiểm tra trùng số điện thoại
    existing_phone = session.exec(
        select(Customer).where(Customer.phone_number == phone_number)
    ).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Số điện thoại đã tồn tại trong hệ thống",
        )

    # Kiểm tra user_id nếu có
    if data.user_id:
        user = session.get(User, data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tài khoản người dùng liên kết không tồn tại",
            )
        existing_user_link = session.exec(
            select(Customer).where(Customer.user_id == data.user_id)
        ).first()
        if existing_user_link:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tài khoản người dùng đã được liên kết với một khách hàng khác",
            )

    customer = Customer(
        full_name=full_name,
        phone_number=phone_number,
        email=data.email,
        address=data.address.strip() if data.address else None,
        user_id=data.user_id,
        created_at=get_datetime_utc(),
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)

    return CustomerPublic.model_validate(customer)


def get_customer_by_id(
    session: Session,
    customer_id: uuid.UUID,
    current_user: User | None = None,
) -> CustomerPublic:
    """Lấy chi tiết một khách hàng. Khách hàng thông thường chỉ được xem của chính mình."""
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin khách hàng",
        )

    # Kiểm tra quyền: nếu là customer và không phải superuser, chỉ xem hồ sơ của mình
    if current_user and not current_user.is_superuser:
        role = (current_user.role or "").lower()
        if role == "customer" and customer.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền truy cập thông tin khách hàng này",
            )

    return CustomerPublic.model_validate(customer)


def update_customer(
    session: Session,
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    current_user: User | None = None,
) -> CustomerPublic:
    """Cập nhật thông tin khách hàng với kiểm tra trùng SĐT và phân quyền."""
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin khách hàng",
        )

    if current_user and not current_user.is_superuser:
        role = (current_user.role or "").lower()
        if role == "customer" and customer.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền chỉnh sửa thông tin khách hàng này",
            )

    update_dict = data.model_dump(exclude_unset=True)

    if "phone_number" in update_dict and update_dict["phone_number"] is not None:
        new_phone = update_dict["phone_number"].strip()
        if len(new_phone) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Số điện thoại phải có ít nhất 8 chữ số",
            )
        # Kiểm tra trùng SĐT với khách hàng khác
        duplicate = session.exec(
            select(Customer).where(
                Customer.phone_number == new_phone, Customer.id != customer_id
            )
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Số điện thoại đã thuộc về khách hàng khác",
            )
        update_dict["phone_number"] = new_phone

    if "full_name" in update_dict and update_dict["full_name"] is not None:
        update_dict["full_name"] = update_dict["full_name"].strip()

    if "address" in update_dict and update_dict["address"] is not None:
        update_dict["address"] = update_dict["address"].strip()

    update_dict["updated_at"] = get_datetime_utc()
    customer.sqlmodel_update(update_dict)
    session.add(customer)
    session.commit()
    session.refresh(customer)

    return CustomerPublic.model_validate(customer)


def delete_customer(
    session: Session,
    customer_id: uuid.UUID,
) -> Message:
    """Xóa khách hàng khi chưa có dữ liệu lịch hẹn hoặc hóa đơn liên quan."""
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin khách hàng",
        )

    # Kiểm tra ràng buộc lịch hẹn và hóa đơn
    has_appointments = session.exec(
        select(Appointment.id).where(Appointment.customer_id == customer_id)
    ).first()
    if has_appointments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa khách hàng đã có lịch hẹn hoặc dữ liệu sửa chữa liên quan",
        )

    has_invoices = session.exec(
        select(Invoice.id).where(Invoice.customer_id == customer_id)
    ).first()
    if has_invoices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa khách hàng đã có thông tin hóa đơn tài chính liên quan",
        )

    session.delete(customer)
    session.commit()
    return Message(message="Xóa khách hàng thành công")
