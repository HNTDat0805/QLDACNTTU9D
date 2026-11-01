"""Demo-specific authorization regression, isolated by the test engine fixture."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Customer, Technician
from tests.api.routes.test_commerce_workflow import account, order


def test_intake_rejects_unassigned_technician(client: TestClient, db: Session) -> None:
    owner, owner_headers = account(db, "customer")
    assigned_user, assigned_headers = account(db, "technician")
    _, other_tech_headers = account(db, "technician")
    appointment = order(db, owner, "CONFIRMED")
    technician = Technician(full_name="Assigned fixture", user_id=assigned_user.id)
    db.add(technician)
    db.flush()
    appointment.technician_id = technician.id
    db.add(appointment)
    db.commit()
    body = {
        "appointment_id": str(appointment.id),
        "physical_condition": "Fixture condition",
        "fault_description": "Fixture fault",
    }
    assert client.post("/api/v1/intake", json=body).status_code == 401
    assert (
        client.post("/api/v1/intake", headers=owner_headers, json=body).status_code
        == 403
    )
    assert (
        client.post("/api/v1/intake", headers=other_tech_headers, json=body).status_code
        == 403
    )
    db.refresh(appointment)
    assert appointment.customer_notes is None
    assert (
        client.post("/api/v1/intake", headers=assigned_headers, json=body).status_code
        == 201
    )


def test_customer_catalog_role_policy(client: TestClient, db: Session) -> None:
    """User confirmed technician catalog visibility; customer privacy stays scoped."""
    owner, owner_headers = account(db, "customer")
    _, other_customer_headers = account(db, "customer")
    _, technician_headers = account(db, "technician")
    customer = Customer(
        full_name="Fixture customer", phone_number=owner.id.hex[:15], user_id=owner.id
    )
    db.add(customer)
    db.commit()
    own_detail = client.get(f"/api/v1/customers/{customer.id}", headers=owner_headers)
    other_detail = client.get(
        f"/api/v1/customers/{customer.id}", headers=other_customer_headers
    )
    customer_catalog = client.get("/api/v1/customers", headers=owner_headers)
    technician_catalog = client.get("/api/v1/customers", headers=technician_headers)
    technician_detail = client.get(
        f"/api/v1/customers/{customer.id}", headers=technician_headers
    )
    assert own_detail.status_code == 200
    assert other_detail.status_code == 403
    assert customer_catalog.status_code == 403
    assert technician_catalog.status_code == 200
    assert technician_detail.status_code == 200
