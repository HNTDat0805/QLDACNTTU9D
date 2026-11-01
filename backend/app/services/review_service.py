import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, col, func, select

from app.models import (
    Appointment,
    AppointmentService,
    AppointmentStatus,
    Customer,
    Review,
    ReviewCreateRequest,
    ReviewPublic,
    ReviewsPublic,
    User,
)


def create_review(
    session: Session,
    data: ReviewCreateRequest,
    current_user: User,
) -> ReviewPublic:
    """
    Tiếp nhận và xử lý đánh giá chất lượng dịch vụ từ khách hàng (Task 393).

    Quy tắc nghiệp vụ:
    1. Lịch hẹn sửa chữa phải tồn tại (404 Not Found nếu không tìm thấy).
    2. Trạng thái lịch hẹn phải là COMPLETED (400 Bad Request nếu chưa hoàn thành).
    3. Quyền của khách hàng: Chỉ khách hàng sở hữu lịch hẹn (hoặc Admin/Manager) mới được đánh giá (403 Forbidden).
    4. Chống đánh giá trùng: Mỗi lịch hẹn chỉ được đánh giá duy nhất 1 lần (409 Conflict).
    5. Điểm đánh giá phải từ 1 đến 5 sao (422 Unprocessable Entity nếu không hợp lệ).
    6. Tự động liên kết customer_id và technician_id từ lịch hẹn.
    """
    # 1. Kiểm tra lịch hẹn tồn tại
    appointment = session.get(Appointment, data.appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lịch hẹn không tồn tại",
        )

    # 2. Kiểm tra trạng thái lịch hẹn: Phải là COMPLETED
    appt_status = (appointment.status or "").upper()
    if appt_status != AppointmentStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Chỉ có thể đánh giá cho lịch hẹn sửa chữa đã hoàn thành "
                f"(trạng thái hiện tại: {appointment.status})"
            ),
        )

    # 3. Kiểm tra phân quyền: Khách hàng sở hữu lịch hẹn
    is_privileged = current_user.is_superuser or (current_user.role or "").lower() in (
        "admin",
        "manager",
    )
    customer = session.exec(
        select(Customer).where(col(Customer.user_id) == current_user.id)
    ).first()

    if not is_privileged:
        if customer is None or customer.id != appointment.customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền đánh giá lịch hẹn của khách hàng khác",
            )

    # 4. Ngăn chặn đánh giá trùng lặp cho cùng một lịch hẹn
    existing_review = session.exec(
        select(Review).where(col(Review.appointment_id) == appointment.id)
    ).first()
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lịch hẹn này đã được đánh giá trước đó",
        )

    # 5. Kiểm tra điểm đánh giá (1 - 5)
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Điểm đánh giá phải từ 1 đến 5 sao",
        )

    # 6. Ghi nhận đánh giá và liên kết
    review = Review(
        appointment_id=appointment.id,
        customer_id=appointment.customer_id,
        technician_id=appointment.technician_id,
        rating=data.rating,
        comment=data.comment.strip() if data.comment and data.comment.strip() else None,
    )
    session.add(review)
    session.commit()
    session.refresh(review)

    c_name = appointment.customer.full_name if appointment.customer else None
    t_name = appointment.technician.full_name if appointment.technician else None
    appt_no = appointment.appointment_number

    return ReviewPublic(
        id=review.id,
        appointment_id=review.appointment_id,
        customer_id=review.customer_id,
        technician_id=review.technician_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        customer_name=c_name,
        technician_name=t_name,
        appointment_number=appt_no,
    )


def get_reviews(
    session: Session,
    skip: int = 0,
    limit: int = 20,
    service_id: uuid.UUID | None = None,
    appointment_id: uuid.UUID | None = None,
    rating: int | None = None,
) -> ReviewsPublic:
    """
    Truy xuất danh sách đánh giá dịch vụ có phân trang và bộ lọc (Task 393).
    Hỗ trợ lọc theo service_id, appointment_id hoặc rating.
    """
    query = select(Review)
    count_query = select(func.count()).select_from(Review)
    avg_query = select(func.avg(col(Review.rating))).select_from(Review)

    if appointment_id:
        query = query.where(col(Review.appointment_id) == appointment_id)
        count_query = count_query.where(col(Review.appointment_id) == appointment_id)
        avg_query = avg_query.where(col(Review.appointment_id) == appointment_id)

    if rating is not None:
        query = query.where(col(Review.rating) == rating)
        count_query = count_query.where(col(Review.rating) == rating)
        avg_query = avg_query.where(col(Review.rating) == rating)

    if service_id:
        query = (
            query.join(Appointment, col(Review.appointment_id) == col(Appointment.id))
            .join(
                AppointmentService,
                col(Appointment.id) == col(AppointmentService.appointment_id),
            )
            .where(col(AppointmentService.service_id) == service_id)
        )
        count_query = (
            count_query.join(
                Appointment, col(Review.appointment_id) == col(Appointment.id)
            )
            .join(
                AppointmentService,
                col(Appointment.id) == col(AppointmentService.appointment_id),
            )
            .where(col(AppointmentService.service_id) == service_id)
        )
        avg_query = (
            avg_query.join(
                Appointment, col(Review.appointment_id) == col(Appointment.id)
            )
            .join(
                AppointmentService,
                col(Appointment.id) == col(AppointmentService.appointment_id),
            )
            .where(col(AppointmentService.service_id) == service_id)
        )

    total = session.exec(count_query).one()
    avg_val = session.exec(avg_query).one_or_none()
    average_rating = round(float(avg_val), 1) if avg_val is not None else None

    reviews = session.exec(
        query.order_by(col(Review.created_at).desc()).offset(skip).limit(limit)
    ).all()

    data: list[ReviewPublic] = []
    for r in reviews:
        c_name = r.customer.full_name if r.customer else None
        t_name = r.technician.full_name if r.technician else None
        appt_no = r.appointment.appointment_number if r.appointment else None
        data.append(
            ReviewPublic(
                id=r.id,
                appointment_id=r.appointment_id,
                customer_id=r.customer_id,
                technician_id=r.technician_id,
                rating=r.rating,
                comment=r.comment,
                created_at=r.created_at,
                customer_name=c_name,
                technician_name=t_name,
                appointment_number=appt_no,
            )
        )

    return ReviewsPublic(data=data, count=total, average_rating=average_rating)


def get_review_by_id(
    session: Session,
    review_id: uuid.UUID,
) -> ReviewPublic:
    """
    Truy xuất chi tiết một đánh giá theo ID (Task 393).
    """
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đánh giá",
        )

    c_name = review.customer.full_name if review.customer else None
    t_name = review.technician.full_name if review.technician else None
    appt_no = review.appointment.appointment_number if review.appointment else None

    return ReviewPublic(
        id=review.id,
        appointment_id=review.appointment_id,
        customer_id=review.customer_id,
        technician_id=review.technician_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        customer_name=c_name,
        technician_name=t_name,
        appointment_number=appt_no,
    )
