from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.api.routes import appointments as appointments_route
from app.api.routes import slots as slots_route
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestLoggingMiddleware

# Initialize logging configuration early
setup_logging()
logger = get_logger("app.main")

FRONTEND_DIR = Path(__file__).parent / "frontend"


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.FASTAPI_ENV != "development":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    logger.info(
        f"Starting {settings.PROJECT_NAME} (env={settings.FASTAPI_ENV or 'production'}, "
        f"log_level={settings.LOG_LEVEL}, log_format={settings.LOG_FORMAT})"
    )
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Request logging & correlation ID middleware
app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_HOST],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
# Direct /api route aliases matching proposed endpoints without /v1
app.include_router(slots_route.router, prefix="/api")
app.include_router(appointments_route.router, prefix="/api")
app.include_router(appointments_route.bookings_router, prefix="/api")
if FRONTEND_DIR.exists():
    app.frontend("/", directory=FRONTEND_DIR)
