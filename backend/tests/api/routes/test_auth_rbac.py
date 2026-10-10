import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import (
    RequireAdmin,
    RequireCustomer,
    RequireManager,
    RequireStaff,
    require_role,
)
from app.core import security
from app.core.config import settings
from app.core.security import verify_password
from app.crud import create_user
from app.main import app
from app.models import User, UserCreate, UserRole
from tests.utils.utils import random_email

# Create a temporary test router on app to test role authorization dependencies
rbac_test_router = APIRouter(prefix="/test-rbac", tags=["test-rbac"])


@rbac_test_router.get("/customer-only")
def customer_endpoint(user: RequireCustomer):
    return {"message": "hello customer", "role": user.role}


@rbac_test_router.get("/staff-only")
def staff_endpoint(user: RequireStaff):
    return {"message": "hello staff", "role": user.role}


@rbac_test_router.get("/manager-only")
def manager_endpoint(user: RequireManager):
    return {"message": "hello manager", "role": user.role}


@rbac_test_router.get("/admin-only")
def admin_endpoint(user: RequireAdmin):
    return {"message": "hello admin", "role": user.role}


@rbac_test_router.get("/custom-roles")
def custom_roles_endpoint(
    user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
):
    return {"message": "hello manager/admin", "role": user.role}


# Include test router if not already included
if not getattr(app.state, "_rbac_router_included", False):
    app.include_router(rbac_test_router)
    app.state._rbac_router_included = True


# Helper function to create users with specific roles
def create_test_user_with_role(
    db: Session,
    role: str = "customer",
    is_active: bool = True,
    is_superuser: bool = False,
    password: str = "password123",
) -> tuple[User, str]:
    email = random_email()
    user_in = UserCreate(
        email=email,
        password=password,
        full_name=f"Test {role.title()}",
        role=role,
        is_active=is_active,
        is_superuser=is_superuser,
    )
    user = create_user(session=db, user_create=user_in)
    return user, password


# ============================================================================
# 1. REGISTER TESTS
# ============================================================================


def test_register_success(client: TestClient, db: Session) -> None:
    email = random_email()
    password = "secretPassword123"
    full_name = "Nguyen Van A"

    response = client.post(
        f"{settings.API_V1_STR}/login/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["full_name"] == full_name
    assert data["role"] == "customer"
    assert "hashed_password" not in data
    assert "password" not in data

    # Verify database state
    user = db.get(User, uuid.UUID(data["id"]))
    assert user is not None
    assert user.role == "customer"
    assert user.is_superuser is False
    # Verify password was hashed and not plaintext
    assert user.hashed_password != password
    verified, _ = verify_password(password, user.hashed_password)
    assert verified is True


def test_register_duplicate_email(client: TestClient, db: Session) -> None:
    user, _ = create_test_user_with_role(db, role="customer")
    response = client.post(
        f"{settings.API_V1_STR}/login/register",
        json={
            "email": user.email,
            "password": "validPassword123",
            "full_name": "Duplicate User",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_register_invalid_data(client: TestClient) -> None:
    # Invalid email
    response = client.post(
        f"{settings.API_V1_STR}/login/register",
        json={"email": "not-an-email", "password": "validPassword123"},
    )
    assert response.status_code == 422

    # Password too short (min 8)
    response = client.post(
        f"{settings.API_V1_STR}/login/register",
        json={"email": random_email(), "password": "short"},
    )
    assert response.status_code == 422


def test_register_cannot_escalate_role(client: TestClient, db: Session) -> None:
    email = random_email()
    password = "secretPassword123"

    # Attempt to inject role=admin and is_superuser=True
    response = client.post(
        f"{settings.API_V1_STR}/login/register",
        json={
            "email": email,
            "password": password,
            "role": "admin",
            "is_superuser": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "customer"
    assert data["is_superuser"] is False

    # Check directly in database
    user = db.get(User, uuid.UUID(data["id"]))
    assert user is not None
    assert user.role == "customer"
    assert user.is_superuser is False


# ============================================================================
# 2. LOGIN TESTS
# ============================================================================


def test_login_success(client: TestClient, db: Session) -> None:
    user, password = create_test_user_with_role(db, role="customer")
    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "password" not in data
    assert "hashed_password" not in data

    # Verify access token payload
    access_payload = security.decode_token(data["access_token"])
    assert access_payload["sub"] == str(user.id)
    assert access_payload["type"] == "access"
    assert access_payload["role"] == "customer"
    assert access_payload["email"] == user.email
    assert "exp" in access_payload
    assert "iat" in access_payload

    # Verify refresh token payload
    refresh_payload = security.decode_token(data["refresh_token"])
    assert refresh_payload["sub"] == str(user.id)
    assert refresh_payload["type"] == "refresh"
    assert "exp" in refresh_payload
    assert "iat" in refresh_payload


def test_login_incorrect_password(client: TestClient, db: Session) -> None:
    user, _ = create_test_user_with_role(db, role="customer")
    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": "wrongpassword123"},
    )
    assert response.status_code == 400
    assert "incorrect email or password" in response.json()["detail"].lower()


def test_login_user_not_found(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": "nonexistent@fixphone.vn", "password": "password123"},
    )
    assert response.status_code == 400
    assert "incorrect email or password" in response.json()["detail"].lower()


def test_login_inactive_user(client: TestClient, db: Session) -> None:
    user, password = create_test_user_with_role(db, role="customer", is_active=False)
    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    assert response.status_code == 400
    assert "inactive user" in response.json()["detail"].lower()


# ============================================================================
# 3. JWT AUTHENTICATION TESTS
# ============================================================================


def test_jwt_valid_token(client: TestClient, db: Session) -> None:
    user, password = create_test_user_with_role(db, role="customer")
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    token = login_res.json()["access_token"]

    res = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["email"] == user.email


def test_jwt_missing_token(client: TestClient) -> None:
    res = client.post(f"{settings.API_V1_STR}/login/test-token")
    assert res.status_code == 401


def test_jwt_expired_token(client: TestClient, db: Session) -> None:
    user, _ = create_test_user_with_role(db, role="customer")
    expired_token = security.create_access_token(
        subject=user.id,
        expires_delta=timedelta(seconds=-10),
    )
    res = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401


def test_jwt_invalid_signature(client: TestClient, db: Session) -> None:
    user, _ = create_test_user_with_role(db, role="customer")
    # Encode with invalid secret key
    payload = {
        "sub": str(user.id),
        "type": "access",
        "exp": datetime.now(UTC) + timedelta(minutes=15),
    }
    fake_token = jwt.encode(payload, "wrong_secret_key", algorithm="HS256")
    res = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers={"Authorization": f"Bearer {fake_token}"},
    )
    assert res.status_code == 401


def test_jwt_invalid_token_type(client: TestClient, db: Session) -> None:
    user, _ = create_test_user_with_role(db, role="customer")
    # Generate token with wrong type
    payload = {
        "sub": str(user.id),
        "type": "invalid_type",
        "exp": datetime.now(UTC) + timedelta(minutes=15),
    }
    invalid_type_token = jwt.encode(
        payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    res = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers={"Authorization": f"Bearer {invalid_type_token}"},
    )
    assert res.status_code == 401
    assert "invalid token type" in res.json()["detail"].lower()


# ============================================================================
# 4. REFRESH TOKEN TESTS
# ============================================================================


def test_refresh_token_success(client: TestClient, db: Session) -> None:
    user, password = create_test_user_with_role(db, role="customer")
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    refresh_token = login_res.json()["refresh_token"]

    # Call refresh endpoint
    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Use the newly granted access token
    test_res = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert test_res.status_code == 200


def test_refresh_token_cannot_be_used_as_access_token(
    client: TestClient, db: Session
) -> None:
    user, password = create_test_user_with_role(db, role="customer")
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    refresh_token = login_res.json()["refresh_token"]

    # Attempt to use refresh token on endpoint requiring access token
    res = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert res.status_code == 401
    assert "access token required" in res.json()["detail"].lower()


def test_access_token_cannot_be_used_as_refresh_token(
    client: TestClient, db: Session
) -> None:
    user, password = create_test_user_with_role(db, role="customer")
    login_res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    access_token = login_res.json()["access_token"]

    # Attempt to call refresh endpoint with an access token
    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": access_token},
    )
    assert res.status_code == 401
    assert "refresh token required" in res.json()["detail"].lower()


def test_refresh_token_expired(client: TestClient, db: Session) -> None:
    user, _ = create_test_user_with_role(db, role="customer")
    expired_refresh = security.create_refresh_token(
        subject=user.id,
        expires_delta=timedelta(seconds=-10),
    )
    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": expired_refresh},
    )
    assert res.status_code == 401


def test_refresh_token_invalid_signature(client: TestClient, db: Session) -> None:
    user, _ = create_test_user_with_role(db, role="customer")
    payload = {
        "sub": str(user.id),
        "type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=7),
    }
    fake_token = jwt.encode(payload, "invalid_secret", algorithm="HS256")
    res = client.post(
        f"{settings.API_V1_STR}/login/refresh-token",
        json={"refresh_token": fake_token},
    )
    assert res.status_code == 401


# ============================================================================
# 5. ROLE-BASED ACCESS CONTROL (RBAC) TESTS
# ============================================================================


def test_rbac_customer_access(client: TestClient, db: Session) -> None:
    customer, pwd = create_test_user_with_role(db, role="customer")
    res = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": customer.email, "password": pwd},
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Customer accessing customer endpoint -> 200
    res = client.get("/test-rbac/customer-only", headers=headers)
    assert res.status_code == 200

    # Customer accessing staff endpoint -> 403 Forbidden
    res = client.get("/test-rbac/staff-only", headers=headers)
    assert res.status_code == 403

    # Customer accessing manager endpoint -> 403 Forbidden
    res = client.get("/test-rbac/manager-only", headers=headers)
    assert res.status_code == 403

    # Customer accessing admin endpoint -> 403 Forbidden
    res = client.get("/test-rbac/admin-only", headers=headers)
    assert res.status_code == 403


def test_rbac_staff_and_technician_access(client: TestClient, db: Session) -> None:
    # Staff
    staff, pwd_staff = create_test_user_with_role(db, role="staff")
    staff_token = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": staff.email, "password": pwd_staff},
    ).json()["access_token"]
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    # Technician
    tech, pwd_tech = create_test_user_with_role(db, role="technician")
    tech_token = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": tech.email, "password": pwd_tech},
    ).json()["access_token"]
    tech_headers = {"Authorization": f"Bearer {tech_token}"}

    # Both staff and technician can access staff-only endpoint
    assert client.get("/test-rbac/staff-only", headers=staff_headers).status_code == 200
    assert client.get("/test-rbac/staff-only", headers=tech_headers).status_code == 200

    # Neither staff nor technician can access manager-only or admin-only
    assert (
        client.get("/test-rbac/manager-only", headers=staff_headers).status_code == 403
    )
    assert client.get("/test-rbac/admin-only", headers=tech_headers).status_code == 403


def test_rbac_manager_access(client: TestClient, db: Session) -> None:
    manager, pwd = create_test_user_with_role(db, role="manager")
    token = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": manager.email, "password": pwd},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Manager can access manager-only
    assert client.get("/test-rbac/manager-only", headers=headers).status_code == 200
    # Manager can access staff-only (manager is in staff hierarchy)
    assert client.get("/test-rbac/staff-only", headers=headers).status_code == 200
    # Manager cannot access admin-only
    assert client.get("/test-rbac/admin-only", headers=headers).status_code == 403


def test_rbac_admin_access(client: TestClient, db: Session) -> None:
    admin, pwd = create_test_user_with_role(db, role="admin")
    token = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": admin.email, "password": pwd},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Admin can access admin-only, manager-only, staff-only
    assert client.get("/test-rbac/admin-only", headers=headers).status_code == 200
    assert client.get("/test-rbac/manager-only", headers=headers).status_code == 200
    assert client.get("/test-rbac/staff-only", headers=headers).status_code == 200


def test_rbac_unauthenticated_returns_401(client: TestClient) -> None:
    assert client.get("/test-rbac/customer-only").status_code == 401
    assert client.get("/test-rbac/staff-only").status_code == 401
    assert client.get("/test-rbac/manager-only").status_code == 401
    assert client.get("/test-rbac/admin-only").status_code == 401
