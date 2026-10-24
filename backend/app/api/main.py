from fastapi import APIRouter

from app.api.routes import (
    appointments,
    customers,
    items,
    login,
    private,
    queue,
    slots,
    technicians,
    users,
    utils,
    work_schedules,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(slots.router)
api_router.include_router(appointments.router)
api_router.include_router(appointments.bookings_router)
api_router.include_router(customers.router)
api_router.include_router(technicians.router)
api_router.include_router(work_schedules.router)
api_router.include_router(queue.router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
