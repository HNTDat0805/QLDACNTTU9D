import uuid
from collections.abc import Callable, Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, User, UserRole

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except InvalidTokenError, ValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token_data.type is not None and token_data.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not token_data.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = uuid.UUID(token_data.sub)
    except ValueError, TypeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

reusable_oauth2_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    auto_error=False,
)


def get_current_user_optional(
    session: SessionDep,
    token: Annotated[str | None, Depends(reusable_oauth2_optional)] = None,
) -> User | None:
    if not token:
        return None
    return get_current_user(session=session, token=token)


CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]


def require_role(*allowed_roles: str | UserRole) -> Callable[[User], User]:
    """
    Authorization dependency verifying that current user has one of allowed roles.
    Raises 403 Forbidden if user is authenticated but not authorized.
    Superusers automatically bypass role checks.
    """
    normalized_allowed = {
        (r.value if isinstance(r, UserRole) else str(r)).lower() for r in allowed_roles
    }

    def role_checker(current_user: CurrentUser) -> User:
        user_role = (current_user.role or "").lower()
        if current_user.is_superuser:
            return current_user
        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user

    return role_checker


RequireAdmin = Annotated[User, Depends(require_role(UserRole.ADMIN, "admin"))]
RequireManager = Annotated[
    User, Depends(require_role(UserRole.ADMIN, UserRole.MANAGER, "admin", "manager"))
]
RequireStaff = Annotated[
    User,
    Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.STAFF,
            UserRole.TECHNICIAN,
            "admin",
            "manager",
            "staff",
            "technician",
        )
    ),
]
RequireCustomer = Annotated[User, Depends(require_role(UserRole.CUSTOMER, "customer"))]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user
