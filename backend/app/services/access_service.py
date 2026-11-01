import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import Appointment, Customer, Technician, User


def is_reception(user: User) -> bool:
    return user.is_superuser or user.role in ("admin", "manager", "staff")


def check_appointment_access(
    session: Session, user: User, appointment: Appointment
) -> None:
    if is_reception(user):
        return
    if user.role == "technician":
        technician = session.exec(
            select(Technician).where(Technician.user_id == user.id)
        ).first()
        if technician and technician.id == appointment.technician_id:
            return
    elif user.role == "customer":
        customer = session.get(Customer, appointment.customer_id)
        if customer and customer.user_id == user.id:
            return
    raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập phiếu này")


def accessible_appointment_ids(session: Session, user: User) -> list[uuid.UUID] | None:
    if is_reception(user):
        return None
    if user.role == "technician":
        statement = (
            select(Appointment.id).join(Technician).where(Technician.user_id == user.id)
        )
    elif user.role == "customer":
        statement = (
            select(Appointment.id).join(Customer).where(Customer.user_id == user.id)
        )
    else:
        raise HTTPException(status_code=403, detail="Không đủ quyền truy cập")
    return list(session.exec(statement).all())
