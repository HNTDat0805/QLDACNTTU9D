from fastapi import APIRouter

from app.api.routes import appointments, items, login, private, slots, users, utils
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(slots.router)
api_router.include_router(appointments.router)
api_router.include_router(appointments.bookings_router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
