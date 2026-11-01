import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import security
from app.crud import create_user
from app.models import (
    Appointment,
    AppointmentService,
    AppointmentStatus,
    Customer,
    Device,
    Review,
    Service,
    Technician,
    User,
    UserCreate,
)
from tests.utils.utils import random_email


def get_token_headers(user: User) -> dict[str, str]:
    token = security.create_access_token(
        subject=user.id, role=user.role, email=user.email
    )
    return {"Authorization": f"Bearer {token}"}


def create_role_user(db: Session, role: str) -> User:
    email = random_email()
    user_in = UserCreate(
        email=email,
        password="testPassword123",
        full_name=f"Test {role.title()}",
        role=role,
    )
    return create_user(session=db, user_create=user_in)


def setup_customer_appointment(
    db: Session,
    status: str = AppointmentStatus.COMPLETED.value,
) -> tuple[User, Customer, Technician, Appointment, Service]:
    # Tạo user customer
    user = create_role_user(db, "customer")

    # Tạo customer profile liên kết với user
    customer = Customer(
        user_id=user.id,
        full_name="Nguyễn Văn Test",
        phone_number=f"091{uuid.uuid4().int % 10000000:07d}",
        email=user.email,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    # Thiết bị
    device = Device(
        customer_id=customer.id,
        brand="Apple",
        model="iPhone 14 Pro",
        color="Deep Purple",
    )
    db.add(device)

    # Kỹ thuật viên
    tech = Technician(
        full_name="KTV Nguyễn Văn Hùng",
        phone_number=f"098{uuid.uuid4().int % 10000000:07d}",
        is_active=True,
    )
    db.add(tech)

    # Dịch vụ
    service = Service(
        code=f"SVC-{uuid.uuid4().hex[:6].upper()}",
        name=f"Thay màn hình OLED {uuid.uuid4().hex[:4]}",
        base_price=1_500_000.0,
        estimated_duration_minutes=45,
        is_active=True,
    )
    db.add(service)
    db.commit()

    # Lịch hẹn
    appointment = Appointment(
        appointment_number=f"APPT-REV-{uuid.uuid4().hex[:6].upper()}",
        appointment_date=datetime.now(UTC),
        status=status,
        customer_id=customer.id,
        device_id=device.id,
        technician_id=tech.id,
        total_amount=1_500_000.0,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    # Dịch vụ trong lịch hẹn
    appt_svc = AppointmentService(
        appointment_id=appointment.id,
        service_id=service.id,
        price_at_booking=1_500_000.0,
        quantity=1,
    )
    db.add(appt_svc)
    db.commit()

    return user, customer, tech, appointment, service


# ============================================================================
# TEST CASES: SERVICE REVIEWS API (Task 393)
# ============================================================================


def test_submit_valid_review(client: TestClient, db: Session) -> None:
    """Test gửi đánh giá hợp lệ khi lịch hẹn đã hoàn thành."""
    user, customer, tech, appt, _ = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )
    headers = get_token_headers(user)

    payload = {
        "appointment_id": str(appt.id),
        "rating": 5,
        "comment": "Dịch vụ rất tốt, nhân viên thân thiện và sửa nhanh!",
    }

    response = client.post("/api/reviews", headers=headers, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 5
    assert data["comment"] == "Dịch vụ rất tốt, nhân viên thân thiện và sửa nhanh!"
    assert data["appointment_id"] == str(appt.id)
    assert data["customer_id"] == str(customer.id)
    assert data["technician_id"] == str(tech.id)
    assert data["appointment_number"] == appt.appointment_number
    assert data["customer_name"] == customer.full_name
    assert data["technician_name"] == tech.full_name


def test_submit_review_api_v1_alias(client: TestClient, db: Session) -> None:
    """Test gửi đánh giá qua endpoint alias /api/v1/reviews."""
    user, _, _, appt, _ = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )
    headers = get_token_headers(user)

    payload = {
        "appointment_id": str(appt.id),
        "rating": 4,
        "comment": "Sửa tốt nhưng thời gian chờ hơi lâu.",
    }

    response = client.post("/api/v1/reviews", headers=headers, json=payload)
    assert response.status_code == 201
    assert response.json()["rating"] == 4


def test_submit_review_missing_data(client: TestClient, db: Session) -> None:
    """Test gửi đánh giá thiếu dữ liệu bắt buộc (appointment_id hoặc rating)."""
    user, _, _, appt, _ = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )
    headers = get_token_headers(user)

    # Thiếu appointment_id
    res_no_appt = client.post(
        "/api/reviews",
        headers=headers,
        json={"rating": 5, "comment": "Tốt"},
    )
    assert res_no_appt.status_code == 422

    # Thiếu rating
    res_no_rating = client.post(
        "/api/reviews",
        headers=headers,
        json={"appointment_id": str(appt.id), "comment": "Tốt"},
    )
    assert res_no_rating.status_code == 422


def test_submit_review_invalid_rating(client: TestClient, db: Session) -> None:
    """Test gửi đánh giá với điểm số không hợp lệ (ngoài khoảng 1 - 5)."""
    user, _, _, appt, _ = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )
    headers = get_token_headers(user)

    # rating = 0 (< 1)
    res_zero = client.post(
        "/api/reviews",
        headers=headers,
        json={"appointment_id": str(appt.id), "rating": 0},
    )
    assert res_zero.status_code == 422

    # rating = 6 (> 5)
    res_six = client.post(
        "/api/reviews",
        headers=headers,
        json={"appointment_id": str(appt.id), "rating": 6},
    )
    assert res_six.status_code == 422

    # rating = -1
    res_neg = client.post(
        "/api/reviews",
        headers=headers,
        json={"appointment_id": str(appt.id), "rating": -1},
    )
    assert res_neg.status_code == 422


def test_submit_review_appointment_not_completed(
    client: TestClient, db: Session
) -> None:
    """Test đánh giá khi không đủ điều kiện nghiệp vụ: Lịch hẹn chưa COMPLETED."""
    for invalid_status in [
        AppointmentStatus.PENDING.value,
        AppointmentStatus.CONFIRMED.value,
        AppointmentStatus.IN_PROGRESS.value,
        AppointmentStatus.CANCELLED.value,
    ]:
        user, _, _, appt, _ = setup_customer_appointment(db, status=invalid_status)
        headers = get_token_headers(user)

        response = client.post(
            "/api/reviews",
            headers=headers,
            json={
                "appointment_id": str(appt.id),
                "rating": 5,
                "comment": "Chưa hoàn thành mà đã đánh giá",
            },
        )
        assert response.status_code == 400
        assert (
            "Chỉ có thể đánh giá cho lịch hẹn sửa chữa đã hoàn thành"
            in response.json()["detail"]
        )


def test_submit_review_duplicate(client: TestClient, db: Session) -> None:
    """Test ngăn chặn đánh giá trùng lặp cho cùng một lịch hẹn."""
    user, _, _, appt, _ = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )
    headers = get_token_headers(user)

    payload = {
        "appointment_id": str(appt.id),
        "rating": 5,
        "comment": "Lần đánh giá thứ nhất",
    }
    # Gửi lần 1 thành công
    res1 = client.post("/api/reviews", headers=headers, json=payload)
    assert res1.status_code == 201

    # Gửi lần 2 báo lỗi trùng 409 Conflict
    payload2 = {
        "appointment_id": str(appt.id),
        "rating": 4,
        "comment": "Lần đánh giá thứ hai trùng lặp",
    }
    res2 = client.post("/api/reviews", headers=headers, json=payload2)
    assert res2.status_code == 409
    assert "đã được đánh giá trước đó" in res2.json()["detail"]


def test_submit_review_unauthorized_user(client: TestClient, db: Session) -> None:
    """Test người dùng truy cập/đánh giá lịch hẹn không thuộc quyền của mình."""
    # Khách hàng A tạo lịch hẹn
    _, _, _, appt_a, _ = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )

    # Khách hàng B đăng nhập
    user_b, _, _, _, _ = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )
    headers_b = get_token_headers(user_b)

    # Khách hàng B cố tình đánh giá lịch hẹn của Khách hàng A
    response = client.post(
        "/api/reviews",
        headers=headers_b,
        json={
            "appointment_id": str(appt_a.id),
            "rating": 1,
            "comment": "Cố tình đánh giá xấu lịch của người khác",
        },
    )
    assert response.status_code == 403
    assert "Bạn không có quyền đánh giá" in response.json()["detail"]


def test_submit_review_appointment_not_found(client: TestClient, db: Session) -> None:
    """Test đánh giá lịch hẹn không tồn tại trong hệ thống."""
    user = create_role_user(db, "customer")
    headers = get_token_headers(user)

    random_id = uuid.uuid4()
    response = client.post(
        "/api/reviews",
        headers=headers,
        json={"appointment_id": str(random_id), "rating": 5},
    )
    assert response.status_code == 404
    assert "Lịch hẹn không tồn tại" in response.json()["detail"]


def test_submit_review_by_admin(client: TestClient, db: Session) -> None:
    """Test quản trị viên có quyền gửi đánh giá thay cho lịch hẹn hoàn thành."""
    admin = create_role_user(db, "admin")
    headers = get_token_headers(admin)

    _, customer, tech, appt, _ = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )

    response = client.post(
        "/api/reviews",
        headers=headers,
        json={
            "appointment_id": str(appt.id),
            "rating": 5,
            "comment": "Khách hàng gửi qua tổng đài, Admin nhập giúp",
        },
    )
    assert response.status_code == 201
    assert response.json()["rating"] == 5
    assert response.json()["customer_id"] == str(customer.id)
    assert response.json()["technician_id"] == str(tech.id)


def test_get_reviews_list_and_filters(client: TestClient, db: Session) -> None:
    """Test truy xuất danh sách đánh giá có phân trang và bộ lọc."""
    # Tạo 2 đánh giá
    u1, _, _, appt1, svc1 = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )
    r1 = Review(
        appointment_id=appt1.id,
        customer_id=appt1.customer_id,
        technician_id=appt1.technician_id,
        rating=5,
        comment="Xuất sắc",
    )
    db.add(r1)

    u2, _, _, appt2, _ = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )
    r2 = Review(
        appointment_id=appt2.id,
        customer_id=appt2.customer_id,
        technician_id=appt2.technician_id,
        rating=3,
        comment="Bình thường",
    )
    db.add(r2)
    db.commit()

    # 1. Lấy tất cả
    res_all = client.get("/api/reviews")
    assert res_all.status_code == 200
    all_data = res_all.json()
    assert all_data["count"] >= 2
    assert all_data["average_rating"] is not None

    # 2. Lọc theo rating = 5
    res_five = client.get("/api/reviews?rating=5")
    assert res_five.status_code == 200
    five_data = res_five.json()
    assert all(item["rating"] == 5 for item in five_data["data"])

    # 3. Lọc theo appointment_id
    res_appt = client.get(f"/api/reviews?appointment_id={appt1.id}")
    assert res_appt.status_code == 200
    appt_data = res_appt.json()
    assert appt_data["count"] == 1
    assert appt_data["data"][0]["appointment_id"] == str(appt1.id)

    # 4. Lọc theo service_id
    res_svc = client.get(f"/api/reviews?service_id={svc1.id}")
    assert res_svc.status_code == 200
    svc_data = res_svc.json()
    assert svc_data["count"] == 1
    assert svc_data["data"][0]["appointment_id"] == str(appt1.id)


def test_get_review_detail(client: TestClient, db: Session) -> None:
    """Test truy xuất chi tiết một đánh giá theo ID."""
    _, cust, tech, appt, _ = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )
    review = Review(
        appointment_id=appt.id,
        customer_id=cust.id,
        technician_id=tech.id,
        rating=4,
        comment="Chi tiết đánh giá thử nghiệm",
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # Lấy chi tiết tồn tại
    response = client.get(f"/api/reviews/{review.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(review.id)
    assert data["rating"] == 4
    assert data["comment"] == "Chi tiết đánh giá thử nghiệm"
    assert data["customer_name"] == cust.full_name
    assert data["technician_name"] == tech.full_name

    # Lấy chi tiết không tồn tại
    res_404 = client.get(f"/api/reviews/{uuid.uuid4()}")
    assert res_404.status_code == 404
    assert "Không tìm thấy đánh giá" in res_404.json()["detail"]


def test_review_unauthenticated(client: TestClient, db: Session) -> None:
    """Test gửi đánh giá mà chưa xác thực (thiếu access token)."""
    _, _, _, appt, _ = setup_customer_appointment(
        db, status=AppointmentStatus.COMPLETED.value
    )
    response = client.post(
        "/api/reviews",
        json={"appointment_id": str(appt.id), "rating": 5},
    )
    assert response.status_code == 401
