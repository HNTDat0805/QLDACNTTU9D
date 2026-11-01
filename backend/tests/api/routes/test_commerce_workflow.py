import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token
from app.models import (
    Appointment,
    Customer,
    Device,
    Notification,
    Quote,
    QuoteItem,
    Service,
    Technician,
    TechnicianSchedule,
    User,
)


def account(db: Session, role: str) -> tuple[User, dict[str, str]]:
    user = User(
        email=f"{uuid.uuid4().hex}@example.test",
        hashed_password="unused-test-hash",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, {"Authorization": f"Bearer {create_access_token(user.id)}"}


def order(db: Session, user: User, state: str = "COMPLETED") -> Appointment:
    customer = Customer(
        full_name="Test customer", phone_number=uuid.uuid4().hex[:15], user_id=user.id
    )
    db.add(customer)
    db.flush()
    device = Device(customer_id=customer.id, brand="Test", model="Phone")
    db.add(device)
    db.flush()
    appointment = Appointment(
        customer_id=customer.id,
        device_id=device.id,
        appointment_number=f"APPT-{uuid.uuid4().hex[:20]}",
        appointment_date=datetime.now(UTC),
        status=state,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def approved_quote(db: Session, appointment: Appointment) -> Quote:
    quote = Quote(
        appointment_id=appointment.id,
        quote_number=f"QUO-{uuid.uuid4().hex[:20]}",
        status="ACCEPTED",
        total_amount=100000,
    )
    db.add(quote)
    db.flush()
    db.add(
        QuoteItem(
            quote_id=quote.id,
            item_name="Sửa máy",
            unit_price=100000,
            quantity=1,
            total_price=100000,
        )
    )
    db.commit()
    db.refresh(quote)
    return quote


def test_technician_account_choices_and_public_privacy(
    client: TestClient, db: Session
) -> None:
    _, manager_headers = account(db, "manager")
    _, customer_headers = account(db, "customer")
    technician_user, _ = account(db, "technician")
    invalid_user, _ = account(db, "customer")
    endpoint = "/api/v1/technicians/accounts"
    assert client.get(endpoint, headers=customer_headers).status_code == 403
    choices = client.get(endpoint, headers=manager_headers)
    assert choices.status_code == 200
    selected = next(
        row for row in choices.json() if row["id"] == str(technician_user.id)
    )
    assert set(selected) == {"id", "full_name", "email"}
    assert (
        client.post(
            "/api/v1/technicians",
            headers=manager_headers,
            json={
                "full_name": "Invalid role",
                "user_id": str(invalid_user.id),
            },
        ).status_code
        == 422
    )
    linked = client.post(
        "/api/v1/technicians",
        headers=manager_headers,
        json={
            "full_name": "Public technician",
            "user_id": str(technician_user.id),
        },
    )
    assert linked.status_code == 201
    assert not any(
        row["id"] == str(technician_user.id)
        for row in client.get(endpoint, headers=manager_headers).json()
    )
    service = Service(
        name="Privacy test", base_price=100000, estimated_duration_minutes=30
    )
    db.add(service)
    db.flush()
    future = date.today() + timedelta(days=20)
    db.add(
        TechnicianSchedule(
            technician_id=uuid.UUID(linked.json()["id"]),
            work_date=future,
            start_time=time(8),
            end_time=time(17),
            status="AVAILABLE",
        )
    )
    db.commit()
    public = client.get(
        "/api/v1/slots/technicians",
        params={"service_id": str(service.id), "slot_date": future.isoformat()},
    )
    assert public.status_code == 200
    row = next(row for row in public.json() if row["id"] == linked.json()["id"])
    assert set(row) == {"id", "full_name", "specialization"}


def test_invoice_payment_owner_and_idempotency(client: TestClient, db: Session) -> None:
    owner, owner_headers = account(db, "customer")
    _, other_headers = account(db, "customer")
    _, staff_headers = account(db, "staff")
    appointment = order(db, owner)
    quote = approved_quote(db, appointment)
    issue = client.post(
        "/api/v1/invoices", headers=staff_headers, json={"quote_id": str(quote.id)}
    )
    assert issue.status_code == 201
    invoice_id = issue.json()["id"]
    assert (
        client.get(f"/api/v1/invoices/{invoice_id}", headers=other_headers).status_code
        == 403
    )
    assert (
        client.get(f"/api/v1/invoices/{invoice_id}", headers=owner_headers).status_code
        == 200
    )
    payload = {
        "amount": "40000",
        "payment_method": "CASH",
        "request_id": str(uuid.uuid4()),
    }
    assert (
        client.post(
            f"/api/v1/invoices/{invoice_id}/payments",
            headers=owner_headers,
            json=payload,
        ).status_code
        == 403
    )
    payment = client.post(
        f"/api/v1/invoices/{invoice_id}/payments", headers=staff_headers, json=payload
    )
    assert payment.status_code == 200
    assert payment.json()["balance"] == 60000
    duplicate = client.post(
        f"/api/v1/invoices/{invoice_id}/payments", headers=staff_headers, json=payload
    )
    assert duplicate.status_code == 200 and len(duplicate.json()["payments"]) == 1
    overpay = {**payload, "amount": "60001", "request_id": str(uuid.uuid4())}
    assert (
        client.post(
            f"/api/v1/invoices/{invoice_id}/payments",
            headers=staff_headers,
            json=overpay,
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/invoices/{invoice_id}/handover", headers=staff_headers
        ).status_code
        == 409
    )
    final = {**payload, "amount": "60000", "request_id": str(uuid.uuid4())}
    assert (
        client.post(
            f"/api/v1/invoices/{invoice_id}/payments", headers=staff_headers, json=final
        ).json()["status"]
        == "PAID"
    )
    assert (
        client.post(
            f"/api/v1/invoices/{invoice_id}/handover", headers=staff_headers
        ).status_code
        == 200
    )


def test_invoice_requires_completed_repair(client: TestClient, db: Session) -> None:
    owner, _ = account(db, "customer")
    _, staff = account(db, "staff")
    quote = approved_quote(db, order(db, owner, "CONFIRMED"))
    assert (
        client.post(
            "/api/v1/invoices", headers=staff, json={"quote_id": str(quote.id)}
        ).status_code
        == 409
    )


def test_me_and_quote_access_are_scoped(client: TestClient, db: Session) -> None:
    owner, owner_headers = account(db, "customer")
    other, other_headers = account(db, "customer")
    appointment = order(db, owner)
    order(db, other)
    quote = approved_quote(db, appointment)
    mine = client.get("/api/v1/appointments/me", headers=owner_headers).json()
    assert [a["id"] for a in mine["data"]] == [str(appointment.id)]
    assert (
        client.get(
            f"/api/v1/appointments/{appointment.id}/detail", headers=other_headers
        ).status_code
        == 403
    )
    assert (
        client.get(f"/api/v1/quotes/{quote.id}", headers=other_headers).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/appointments/{appointment.id}", json={"description": "bad"}
        ).status_code
        == 401
    )


def test_technician_only_sees_assigned_jobs(client: TestClient, db: Session) -> None:
    owner, _ = account(db, "customer")
    technician_user, headers = account(db, "technician")
    appointment = order(db, owner, "CONFIRMED")
    assert (
        client.get(
            f"/api/v1/repair-orders/{appointment.id}", headers=headers
        ).status_code
        == 403
    )
    tech = Technician(full_name="Test technician", user_id=technician_user.id)
    db.add(tech)
    db.flush()
    appointment.technician_id = tech.id
    db.add(appointment)
    db.commit()
    assert (
        client.get(
            f"/api/v1/repair-orders/{appointment.id}", headers=headers
        ).status_code
        == 200
    )
    result = client.get("/api/v1/repair-orders", headers=headers).json()
    assert [a["id"] for a in result["data"]] == [str(appointment.id)]


def test_reviews_and_notifications_are_private(client: TestClient, db: Session) -> None:
    owner, headers = account(db, "customer")
    _, other = account(db, "customer")
    appointment = order(db, owner)
    payload = {"appointment_id": str(appointment.id), "rating": 5, "comment": "Tốt"}
    assert (
        client.post("/api/v1/reviews", headers=other, json=payload).status_code == 403
    )
    assert (
        client.post("/api/v1/reviews", headers=headers, json=payload).status_code == 201
    )
    assert (
        client.post("/api/v1/reviews", headers=headers, json=payload).status_code == 409
    )
    notification = Notification(user_id=owner.id, title="Test", message="Private")
    db.add(notification)
    db.commit()
    assert (
        client.patch(
            f"/api/v1/notifications/{notification.id}/read", headers=other
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/notifications/{notification.id}/read", headers=headers
        ).json()["is_read"]
        is True
    )


def test_statistics_and_service_management_roles(
    client: TestClient, db: Session
) -> None:
    _, customer = account(db, "customer")
    _, manager = account(db, "manager")
    assert client.get("/api/v1/statistics", headers=customer).status_code == 403
    assert client.get("/api/v1/statistics", headers=manager).status_code == 200
    assert client.get("/api/v1/services/manage", headers=customer).status_code == 403
    body = {
        "name": f"Service-{uuid.uuid4().hex}",
        "base_price": 120000,
        "estimated_duration_minutes": 30,
    }
    created = client.post("/api/v1/services", headers=manager, json=body)
    assert created.status_code == 201
    assert client.get(f"/api/v1/services/{created.json()['id']}").status_code == 200


def test_customer_to_handover_workflow(client: TestClient, db: Session) -> None:
    """A full API workflow, with every write confined to the isolated test engine."""
    customer, customer_headers = account(db, "customer")
    technician_user, tech_headers = account(db, "technician")
    _, staff = account(db, "staff")
    day = date.today() + timedelta(days=7)
    technician = Technician(
        full_name="Demo tech", user_id=technician_user.id, is_active=True
    )
    service = Service(
        name=f"Workflow-{uuid.uuid4().hex}",
        base_price=100000,
        estimated_duration_minutes=30,
    )
    db.add(technician)
    db.add(service)
    db.flush()
    db.add(
        TechnicianSchedule(
            technician_id=technician.id,
            work_date=day,
            start_time=time(8),
            end_time=time(18),
            status="AVAILABLE",
        )
    )
    db.commit()
    booking = client.post(
        "/api/v1/appointments",
        headers=customer_headers,
        json={
            "service_id": str(service.id),
            "appointment_date": day.isoformat(),
            "start_time": "09:00",
            "customer_name": "Demo customer",
            "customer_phone": uuid.uuid4().hex[:15],
            "device_brand": "Test",
            "device_model": "Phone",
        },
    )
    assert booking.status_code == 201, booking.json().get("detail")
    appointment_id = booking.json()["appointment_id"]
    mine = client.get("/api/v1/appointments/me", headers=customer_headers).json()
    assert appointment_id in [a["id"] for a in mine["data"]]
    assert client.post(
        f"/api/v1/appointments/{appointment_id}/confirm", headers=staff
    ).status_code in (404, 405)  # HTTP method is PATCH.
    assert (
        client.patch(
            f"/api/v1/appointments/{appointment_id}/confirm", headers=staff
        ).status_code
        == 200
    )
    intake = client.post(
        "/api/v1/intake",
        headers=staff,
        json={
            "appointment_id": appointment_id,
            "physical_condition": "Trầy nhẹ",
            "fault_description": "Pin yếu",
        },
    )
    assert intake.status_code == 201
    assigned = client.patch(
        f"/api/v1/repair-orders/{appointment_id}/technician",
        headers=staff,
        json={"technician_id": str(technician.id), "note": "Phân công sau tiếp nhận"},
    )
    assert assigned.status_code == 200
    diagnosis = client.patch(
        f"/api/v1/repair-orders/{appointment_id}/status",
        headers=tech_headers,
        json={
            "status": "IN_PROGRESS",
            "technician_diagnosis": "Pin chai",
            "note": "Chẩn đoán trước báo giá, chưa thay linh kiện",
        },
    )
    assert diagnosis.status_code == 200
    quotation = client.post(
        "/api/v1/quotes",
        headers=staff,
        json={
            "appointment_id": appointment_id,
            "status": "SENT",
            "items": [{"item_name": "Thay pin", "unit_price": 100000, "quantity": 1}],
        },
    )
    assert quotation.status_code == 201
    quote_id = quotation.json()["data"]["id"]
    assert (
        client.post(
            f"/api/v1/quotes/{quote_id}/accept", headers=customer_headers
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/repair-orders/{appointment_id}/status",
            headers=tech_headers,
            json={"status": "COMPLETED", "note": "Đã kiểm tra xong"},
        ).status_code
        == 200
    )
    invoice = client.post(
        "/api/v1/invoices", headers=staff, json={"quote_id": quote_id}
    )
    assert invoice.status_code == 201
    invoice_id = invoice.json()["id"]
    payment = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        headers=staff,
        json={
            "amount": "100000",
            "payment_method": "CASH",
            "request_id": str(uuid.uuid4()),
        },
    )
    assert payment.status_code == 200 and payment.json()["status"] == "PAID"
    assert (
        client.post(
            f"/api/v1/invoices/{invoice_id}/handover", headers=staff
        ).status_code
        == 200
    )
    assert (
        client.get("/api/v1/notifications", headers=customer_headers).json()["count"]
        >= 3
    )
