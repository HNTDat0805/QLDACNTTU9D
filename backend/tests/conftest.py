import os
from collections.abc import Generator
from urllib.parse import urlsplit, urlunsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, delete

from app.api.deps import get_db
from app.core import db as core_db
from app.core.config import settings
from app.core.db import init_db
from app.core.db_restore import TABLE_MODELS_DELETION_ORDER
from app.main import app
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


def _build_test_db_urls(raw_url: str) -> tuple[str, str, str]:
    parsed = urlsplit(raw_url)
    base_db = (parsed.path or "/app").lstrip("/") or "app"
    test_db = base_db if base_db.endswith("_test") else f"{base_db}_test"
    admin_url = urlunsplit((parsed.scheme, parsed.netloc, "/postgres", parsed.query, parsed.fragment))
    test_url = urlunsplit((parsed.scheme, parsed.netloc, f"/{test_db}", parsed.query, parsed.fragment))
    return admin_url, test_url, test_db


def _init_test_engine() -> Engine:
    if os.environ.get("FIXCARE_TEST_SQLITE") == "1":
        isolated_engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        SQLModel.metadata.create_all(isolated_engine)
        return isolated_engine
    try:
        admin_url, test_url, test_db = _build_test_db_urls(str(settings.DATABASE_URL))
        admin_engine = create_engine(
            admin_url,
            isolation_level="AUTOCOMMIT",
            connect_args={"connect_timeout": 2},
        )
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": test_db},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{test_db}"'))
        admin_engine.dispose()

        pg_engine = create_engine(
            test_url,
            connect_args={"connect_timeout": 2},
        )
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        SQLModel.metadata.drop_all(pg_engine)
        SQLModel.metadata.create_all(pg_engine)
        return pg_engine
    except Exception:
        sqlite_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(sqlite_engine)
        return sqlite_engine


test_engine = _init_test_engine()
core_db.engine = test_engine


def override_get_db() -> Generator[Session]:
    with Session(test_engine) as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session]:
    with Session(test_engine) as session:
        init_db(session)
        yield session
        session.rollback()
        for model in TABLE_MODELS_DELETION_ORDER:
            session.exec(delete(model))
        session.commit()


@pytest.fixture(autouse=True)
def _ensure_clean_session_state(db: Session) -> Generator[None]:
    if not db.is_active:
        db.rollback()
    yield
    if not db.is_active:
        db.rollback()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
