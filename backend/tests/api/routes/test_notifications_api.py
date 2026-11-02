import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import security
from app.crud import create_user
from app.models import (
    Customer,
    Notification,
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


def setup_user_with_customer(
    db: Session, role: str = "customer"
) -> tuple[User, Customer]:
    user = create_role_user(db, role)
    customer = Customer(
        user_id=user.id,
        full_name=user.full_name or "Khách hàng mẫu",
        phone_number=f"093{uuid.uuid4().int % 10000000:07d}",
        email=user.email,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return user, customer


# ============================================================================
# TEST CASES: IN-APP NOTIFICATIONS API (Task 393)
# ============================================================================


def test_get_notifications_list(client: TestClient, db: Session) -> None:
    """Test lấy danh sách thông báo của tài khoản đang đăng nhập."""
    user_a = create_role_user(db, "customer")
    user_b = create_role_user(db, "customer")

    # Tạo 3 thông báo cho User A (2 chưa đọc, 1 đã đọc)
    n1 = Notification(
        user_id=user_a.id,
        title="Lịch hẹn đã xác nhận",
        message="Lịch hẹn sửa chữa APPT-001 đã được xác nhận.",
        notification_type="STATUS_UPDATE",
        is_read=False,
    )
    n2 = Notification(
        user_id=user_a.id,
        title="Báo giá mới",
        message="Báo giá sửa chữa đã có sẵn.",
        notification_type="STATUS_UPDATE",
        is_read=False,
    )
    n3 = Notification(
        user_id=user_a.id,
        title="Thanh toán thành công",
        message="Hóa đơn INV-001 đã thanh toán đủ.",
        notification_type="PAYMENT_CONFIRMATION",
        is_read=True,
    )

    # Tạo 1 thông báo cho User B
    n_b = Notification(
        user_id=user_b.id,
        title="Thông báo riêng User B",
        message="Nội dung bảo mật của User B",
        notification_type="STATUS_UPDATE",
        is_read=False,
    )

    db.add_all([n1, n2, n3, n_b])
    db.commit()

    headers_a = get_token_headers(user_a)
    response = client.get("/api/notifications", headers=headers_a)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert data["unread_count"] == 2
    assert len(data["data"]) == 3

    # Đảm bảo không lộ thông báo của User B
    returned_ids = [item["id"] for item in data["data"]]
    assert str(n_b.id) not in returned_ids


def test_get_notifications_filter_is_read(client: TestClient, db: Session) -> None:
    """Test lọc danh sách thông báo theo trạng thái is_read."""
    user = create_role_user(db, "customer")
    n_unread = Notification(
        user_id=user.id,
        title="Chưa đọc",
        message="Thông báo chưa đọc",
        is_read=False,
    )
    n_read = Notification(
        user_id=user.id,
        title="Đã đọc",
        message="Thông báo đã đọc",
        is_read=True,
    )
    db.add_all([n_unread, n_read])
    db.commit()

    headers = get_token_headers(user)

    # Lọc chưa đọc
    res_unread = client.get("/api/notifications?is_read=false", headers=headers)
    assert res_unread.status_code == 200
    unread_data = res_unread.json()
    assert unread_data["count"] == 1
    assert unread_data["data"][0]["id"] == str(n_unread.id)

    # Lọc đã đọc
    res_read = client.get("/api/notifications?is_read=true", headers=headers)
    assert res_read.status_code == 200
    read_data = res_read.json()
    assert read_data["count"] == 1
    assert read_data["data"][0]["id"] == str(n_read.id)


def test_get_unread_notification_count(client: TestClient, db: Session) -> None:
    """Test lấy số lượng thông báo chưa đọc của tài khoản hiện tại."""
    user = create_role_user(db, "customer")
    db.add(Notification(user_id=user.id, title="TB 1", message="M 1", is_read=False))
    db.add(Notification(user_id=user.id, title="TB 2", message="M 2", is_read=False))
    db.add(Notification(user_id=user.id, title="TB 3", message="M 3", is_read=True))
    db.commit()

    headers = get_token_headers(user)
    response = client.get("/api/notifications/unread-count", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["unread_count"] == 2


def test_mark_single_notification_read(client: TestClient, db: Session) -> None:
    """Test đánh dấu một thông báo đơn lẻ là đã đọc."""
    user = create_role_user(db, "customer")
    notif = Notification(
        user_id=user.id,
        title="Lịch sửa hoàn tất",
        message="Điện thoại của bạn đã sửa xong.",
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    headers = get_token_headers(user)

    # PATCH đánh dấu đã đọc
    response = client.patch(f"/api/notifications/{notif.id}/read", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(notif.id)
    assert data["is_read"] is True

    # Kiểm tra số lượng chưa đọc giảm về 0
    count_res = client.get("/api/notifications/unread-count", headers=headers)
    assert count_res.json()["unread_count"] == 0

    # Test POST alias cũng hoạt động
    notif2 = Notification(user_id=user.id, title="TB 2", message="M 2", is_read=False)
    db.add(notif2)
    db.commit()
    db.refresh(notif2)

    post_res = client.post(f"/api/notifications/{notif2.id}/read", headers=headers)
    assert post_res.status_code == 200
    assert post_res.json()["is_read"] is True


def test_mark_all_notifications_read(client: TestClient, db: Session) -> None:
    """Test đánh dấu tất cả thông báo của người dùng là đã đọc."""
    user = create_role_user(db, "customer")
    db.add(Notification(user_id=user.id, title="T1", message="M1", is_read=False))
    db.add(Notification(user_id=user.id, title="T2", message="M2", is_read=False))
    db.add(Notification(user_id=user.id, title="T3", message="M3", is_read=False))
    db.commit()

    headers = get_token_headers(user)

    # Đánh dấu tất cả đã đọc
    response = client.patch("/api/notifications/read-all", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["updated_count"] == 3
    assert "Đã đánh dấu tất cả thông báo là đã đọc" in data["message"]

    # Kiểm tra lại số lượng chưa đọc = 0
    count_res = client.get("/api/notifications/unread-count", headers=headers)
    assert count_res.json()["unread_count"] == 0


def test_access_notification_other_account(client: TestClient, db: Session) -> None:
    """Test ngăn chặn người dùng truy cập hoặc cập nhật thông báo của tài khoản khác."""
    user_a = create_role_user(db, "customer")
    user_b = create_role_user(db, "customer")

    # Thông báo thuộc User A
    notif_a = Notification(
        user_id=user_a.id,
        title="Thông báo riêng của User A",
        message="Dữ liệu nhạy cảm của A",
        is_read=False,
    )
    db.add(notif_a)
    db.commit()
    db.refresh(notif_a)

    headers_b = get_token_headers(user_b)

    # User B cố tình xem chi tiết thông báo của User A -> 403 Forbidden
    res_get = client.get(f"/api/notifications/{notif_a.id}", headers=headers_b)
    assert res_get.status_code == 403
    assert "Bạn không có quyền truy cập thông báo này" in res_get.json()["detail"]

    # User B cố tình đánh dấu đã đọc thông báo của User A -> 403 Forbidden
    res_patch = client.patch(f"/api/notifications/{notif_a.id}/read", headers=headers_b)
    assert res_patch.status_code == 403
    assert "Bạn không có quyền truy cập thông báo này" in res_patch.json()["detail"]


def test_access_non_existent_notification(client: TestClient, db: Session) -> None:
    """Test truy cập hoặc cập nhật thông báo không tồn tại trong hệ thống."""
    user = create_role_user(db, "customer")
    headers = get_token_headers(user)
    random_id = uuid.uuid4()

    # Xem chi tiết thông báo không tồn tại -> 404
    res_get = client.get(f"/api/notifications/{random_id}", headers=headers)
    assert res_get.status_code == 404
    assert "Thông báo không tồn tại" in res_get.json()["detail"]

    # Đánh dấu đã đọc thông báo không tồn tại -> 404
    res_patch = client.patch(f"/api/notifications/{random_id}/read", headers=headers)
    assert res_patch.status_code == 404
    assert "Thông báo không tồn tại" in res_patch.json()["detail"]


def test_notification_linked_by_customer_id(client: TestClient, db: Session) -> None:
    """Test thông báo được liên kết qua customer_id vẫn hiển thị đúng cho user."""
    user, customer = setup_user_with_customer(db, "customer")

    # Tạo thông báo chỉ gắn customer_id (user_id = None)
    notif = Notification(
        customer_id=customer.id,
        title="Thông báo gửi qua hồ sơ khách hàng",
        message="Kính gửi quý khách...",
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    headers = get_token_headers(user)

    # User truy xuất danh sách
    res_list = client.get("/api/notifications", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json()["count"] == 1
    assert res_list.json()["data"][0]["id"] == str(notif.id)

    # User xem chi tiết
    res_detail = client.get(f"/api/notifications/{notif.id}", headers=headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == str(notif.id)

    # User đánh dấu đã đọc
    res_read = client.patch(f"/api/notifications/{notif.id}/read", headers=headers)
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True


def test_create_in_app_notification_by_staff(client: TestClient, db: Session) -> None:
    """Test nhân viên/quản trị viên tạo thông báo trong ứng dụng cho khách hàng."""
    staff = create_role_user(db, "staff")
    target_user = create_role_user(db, "customer")

    headers_staff = get_token_headers(staff)
    payload = {
        "title": "Nhắc hẹn kiểm tra máy",
        "message": "Quý khách có lịch hẹn ngày mai lúc 10:00.",
        "notification_type": "APPOINTMENT_REMINDER",
        "user_id": str(target_user.id),
        "is_read": False,
    }

    response = client.post("/api/notifications", headers=headers_staff, json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["title"] == "Nhắc hẹn kiểm tra máy"
    assert created["user_id"] == str(target_user.id)

    # Khách hàng không có quyền tự tạo thông báo hệ thống qua API này
    headers_cust = get_token_headers(target_user)
    res_cust = client.post("/api/notifications", headers=headers_cust, json=payload)
    assert res_cust.status_code == 403


def test_notifications_unauthenticated(client: TestClient) -> None:
    """Test truy cập các API thông báo khi chưa đăng nhập (không có token)."""
    assert client.get("/api/notifications").status_code == 401
    assert client.get("/api/notifications/unread-count").status_code == 401
    assert client.patch("/api/notifications/read-all").status_code == 401
    assert client.get(f"/api/notifications/{uuid.uuid4()}").status_code == 401
