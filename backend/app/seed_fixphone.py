"""
DEMO / SEED DATA – FixPhone
Chạy sau khi migration hoàn thành:
    uv run python app/seed_fixphone.py

Dữ liệu này chỉ dùng cho mục đích demo/trình bày. Không phải dữ liệu nghiệp vụ chính thức.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.core.db import engine
from app.core.logging import get_logger, setup_logging
from app.core.security import get_password_hash
from app.models import (
    Appointment,
    AppointmentService,
    Customer,
    Device,
    Invoice,
    InvoiceItem,
    Notification,
    Payment,
    Quote,
    QuoteItem,
    RepairStatusHistory,
    Review,
    Service,
    Technician,
    TechnicianSchedule,
    User,
)

logger = get_logger(__name__)


def now() -> datetime:
    return datetime.now(UTC)


def seed(session: Session) -> None:
    # =========================================================================
    # 1. USERS (with role)
    # =========================================================================
    def get_or_create_user(
        email: str, name: str, role: str, is_superuser: bool = False
    ) -> User:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=email,
                full_name=name,
                hashed_password=get_password_hash("fixphone123"),
                is_active=True,
                is_superuser=is_superuser,
                role=role,
                created_at=now(),
            )
            session.add(user)
            session.flush()
        return user

    admin_user = get_or_create_user(
        "admin@fixphone.vn", "Admin FixPhone", "admin", is_superuser=True
    )
    tech_user_1 = get_or_create_user("tran.hung@fixphone.vn", "Trần Hùng", "technician")
    tech_user_2 = get_or_create_user(
        "nguyen.khoa@fixphone.vn", "Nguyễn Khoa", "technician"
    )
    tech_user_3 = get_or_create_user("le.minh@fixphone.vn", "Lê Minh", "technician")
    cust_user_1 = get_or_create_user(
        "nguyen.van.a@gmail.com", "Nguyễn Văn A", "customer"
    )
    cust_user_2 = get_or_create_user("tran.thi.b@gmail.com", "Trần Thị B", "customer")
    cust_user_3 = get_or_create_user("le.van.c@gmail.com", "Lê Văn C", "customer")
    logger.info("✔ Users seeded")

    # =========================================================================
    # 2. TECHNICIANS
    # =========================================================================
    def get_or_create_technician(
        name: str, phone: str, spec: str, user: User
    ) -> Technician:
        tech = session.exec(
            select(Technician).where(Technician.phone_number == phone)
        ).first()
        if not tech:
            tech = Technician(
                id=uuid.uuid4(),
                full_name=name,
                phone_number=phone,
                specialization=spec,
                is_active=True,
                user_id=user.id,
                created_at=now(),
            )
            session.add(tech)
            session.flush()
        return tech

    tech1 = get_or_create_technician(
        "Trần Hùng", "0901234001", "Màn hình & Camera", tech_user_1
    )
    tech2 = get_or_create_technician(
        "Nguyễn Khoa", "0901234002", "Bo mạch & Nguồn", tech_user_2
    )
    tech3 = get_or_create_technician(
        "Lê Minh", "0901234003", "Pin & Vỏ máy", tech_user_3
    )
    logger.info("✔ Technicians seeded")

    # =========================================================================
    # 3. TECHNICIAN SCHEDULES
    # =========================================================================
    from datetime import date, time

    def add_schedule(tech: Technician, work_date: date, start: time, end: time) -> None:
        existing = session.exec(
            select(TechnicianSchedule)
            .where(TechnicianSchedule.technician_id == tech.id)
            .where(TechnicianSchedule.work_date == work_date)
        ).first()
        if not existing:
            session.add(
                TechnicianSchedule(
                    id=uuid.uuid4(),
                    technician_id=tech.id,
                    work_date=work_date,
                    start_time=start,
                    end_time=end,
                    status="AVAILABLE",
                    created_at=now(),
                )
            )

    today = date.today()
    for i in range(5):
        d = today + timedelta(days=i)
        add_schedule(tech1, d, time(8, 0), time(17, 0))
        add_schedule(tech2, d, time(8, 0), time(17, 0))
        add_schedule(tech3, d, time(8, 0), time(17, 0))
    session.flush()
    logger.info("✔ Technician schedules seeded")

    # =========================================================================
    # 4. CUSTOMERS
    # =========================================================================
    def get_or_create_customer(
        name: str, phone: str, email: str, address: str, user: User
    ) -> Customer:
        c = session.exec(select(Customer).where(Customer.phone_number == phone)).first()
        if not c:
            c = Customer(
                id=uuid.uuid4(),
                full_name=name,
                phone_number=phone,
                email=email,
                address=address,
                user_id=user.id,
                created_at=now(),
            )
            session.add(c)
            session.flush()
        return c

    cust1 = get_or_create_customer(
        "Nguyễn Văn A",
        "0912345001",
        "nguyen.van.a@gmail.com",
        "123 Nguyễn Trãi, Q1, TP.HCM",
        cust_user_1,
    )
    cust2 = get_or_create_customer(
        "Trần Thị B",
        "0912345002",
        "tran.thi.b@gmail.com",
        "456 Lê Lợi, Q3, TP.HCM",
        cust_user_2,
    )
    cust3 = get_or_create_customer(
        "Lê Văn C",
        "0912345003",
        "le.van.c@gmail.com",
        "789 Điện Biên Phủ, Bình Thạnh, TP.HCM",
        cust_user_3,
    )
    logger.info("✔ Customers seeded")

    # =========================================================================
    # 5. DEVICES
    # =========================================================================
    def get_or_create_device(
        customer: Customer, brand: str, model: str, color: str
    ) -> Device:
        d = session.exec(
            select(Device)
            .where(Device.customer_id == customer.id)
            .where(Device.brand == brand)
            .where(Device.model == model)
        ).first()
        if not d:
            d = Device(
                id=uuid.uuid4(),
                customer_id=customer.id,
                device_type="Smartphone",
                brand=brand,
                model=model,
                color=color,
                created_at=now(),
            )
            session.add(d)
            session.flush()
        return d

    device1 = get_or_create_device(cust1, "Apple", "iPhone 13", "Starlight")
    device2 = get_or_create_device(cust1, "Samsung", "S22", "Phantom Black")
    device3 = get_or_create_device(cust2, "Oppo", "A57", "Glowing Black")
    device4 = get_or_create_device(cust3, "Xiaomi", "12", "Blue")
    logger.info("✔ Devices seeded")

    # =========================================================================
    # 6. SERVICES
    # =========================================================================
    services_data = [
        (
            "Thay màn hình iPhone 13",
            "Thay màn hình AMOLED chính hãng cho iPhone 13",
            1_800_000,
            90,
        ),
        ("Thay pin iPhone", "Thay pin dung lượng cao cho iPhone các đời", 350_000, 45),
        (
            "Thay màn hình Samsung S22",
            "Thay màn hình Dynamic AMOLED 2X cho Samsung S22",
            2_200_000,
            90,
        ),
        ("Thay pin Samsung", "Thay pin Samsung dung lượng gốc", 300_000, 45),
        ("Thay màn hình Oppo A57", "Thay màn hình IPS LCD cho Oppo A57", 900_000, 60),
        ("Thay pin Xiaomi 12", "Thay pin Xiaomi 12 dung lượng gốc", 320_000, 45),
        ("Vệ sinh máy", "Vệ sinh bo mạch, cổng sạc, loa, mic toàn diện", 150_000, 30),
        ("Thay cổng sạc", "Thay cổng sạc Type-C / Lightning", 200_000, 45),
        ("Thay kính lưng", "Thay kính lưng nguyên bản", 500_000, 60),
        ("Ép kính cảm ứng", "Ép kính màn hình bị nứt nhẹ không vỡ LCD", 250_000, 45),
    ]

    service_objs: list[Service] = []
    for name, desc, price, duration in services_data:
        svc = session.exec(select(Service).where(Service.name == name)).first()
        if not svc:
            svc = Service(
                id=uuid.uuid4(),
                name=name,
                description=desc,
                base_price=float(price),
                estimated_duration_minutes=duration,
                is_active=True,
                created_at=now(),
            )
            session.add(svc)
            session.flush()
        service_objs.append(svc)
    logger.info("✔ Services seeded")

    # =========================================================================
    # 7. APPOINTMENTS + SERVICES + STATUS HISTORY
    # =========================================================================
    appt_counter = [1]

    def make_appt_number() -> str:
        n = f"APPT-2026-{appt_counter[0]:04d}"
        appt_counter[0] += 1
        return n

    def create_appointment_if_not_exists(
        number: str,
        customer: Customer,
        device: Device,
        technician: Technician,
        appt_date: datetime,
        status: str,
        services: list[tuple[Service, float, int]],
        notes: str = "",
    ) -> Appointment | None:
        existing = session.exec(
            select(Appointment).where(Appointment.appointment_number == number)
        ).first()
        if existing:
            return None

        total = sum(price * qty for _, price, qty in services)
        appt = Appointment(
            id=uuid.uuid4(),
            appointment_number=number,
            customer_id=customer.id,
            device_id=device.id,
            technician_id=technician.id,
            appointment_date=appt_date,
            status=status,
            customer_notes=notes,
            total_amount=total,
            created_at=now(),
        )
        session.add(appt)
        session.flush()

        for svc, price, qty in services:
            session.add(
                AppointmentService(
                    id=uuid.uuid4(),
                    appointment_id=appt.id,
                    service_id=svc.id,
                    price_at_booking=float(price),
                    quantity=qty,
                    created_at=now(),
                )
            )

        # Status history
        session.add(
            RepairStatusHistory(
                id=uuid.uuid4(),
                appointment_id=appt.id,
                previous_status=None,
                new_status="PENDING",
                note="Lịch hẹn được tạo",
                changed_by_user_id=admin_user.id,
                created_at=now() - timedelta(days=2),
            )
        )

        if status in ("IN_PROGRESS", "COMPLETED", "CANCELLED"):
            session.add(
                RepairStatusHistory(
                    id=uuid.uuid4(),
                    appointment_id=appt.id,
                    previous_status="PENDING",
                    new_status="IN_PROGRESS" if status != "CANCELLED" else "CANCELLED",
                    note="Kỹ thuật viên đã nhận máy"
                    if status != "CANCELLED"
                    else "Khách hủy lịch",
                    changed_by_user_id=technician.user_id,
                    created_at=now() - timedelta(days=1),
                )
            )

        if status == "COMPLETED":
            session.add(
                RepairStatusHistory(
                    id=uuid.uuid4(),
                    appointment_id=appt.id,
                    previous_status="IN_PROGRESS",
                    new_status="COMPLETED",
                    note="Sửa chữa hoàn tất, đã trả máy cho khách",
                    changed_by_user_id=technician.user_id,
                    created_at=now(),
                )
            )

        session.flush()
        return appt

    # Appointment 1: Hoàn thành - iPhone 13 thay màn hình + pin
    appt1 = create_appointment_if_not_exists(
        "APPT-2026-0001",
        cust1,
        device1,
        tech1,
        now() - timedelta(days=3),
        "COMPLETED",
        [(service_objs[0], 1_800_000, 1), (service_objs[1], 350_000, 1)],
        "Màn hình bị vỡ góc, pin chai",
    )

    # Appointment 2: Đang xử lý - Samsung S22 thay màn hình
    create_appointment_if_not_exists(
        "APPT-2026-0002",
        cust1,
        device2,
        tech1,
        now() - timedelta(days=1),
        "IN_PROGRESS",
        [(service_objs[2], 2_200_000, 1)],
        "Màn hình bị sọc xanh",
    )

    # Appointment 3: Chờ xử lý - Oppo A57 thay màn hình
    create_appointment_if_not_exists(
        "APPT-2026-0003",
        cust2,
        device3,
        tech3,
        now() + timedelta(days=1),
        "PENDING",
        [(service_objs[4], 900_000, 1), (service_objs[6], 150_000, 1)],
        "Màn hình mờ, máy bẩn",
    )

    # Appointment 4: Hoàn thành - Xiaomi 12 thay pin + vệ sinh
    appt4 = create_appointment_if_not_exists(
        "APPT-2026-0004",
        cust3,
        device4,
        tech2,
        now() - timedelta(days=5),
        "COMPLETED",
        [(service_objs[5], 320_000, 1), (service_objs[6], 150_000, 1)],
        "Pin tụt nhanh, máy bị lag",
    )

    session.flush()
    logger.info("✔ Appointments seeded")

    # =========================================================================
    # 8. QUOTES
    # =========================================================================
    def create_quote_if_not_exists(
        appt: Appointment, items: list[tuple[str, float, int]]
    ) -> Quote | None:
        existing = session.exec(
            select(Quote).where(Quote.appointment_id == appt.id)
        ).first()
        if existing:
            return None
        num = appt.appointment_number.replace("APPT", "QUO")
        total = sum(p * q for _, p, q in items)
        q = Quote(
            id=uuid.uuid4(),
            quote_number=num,
            appointment_id=appt.id,
            total_amount=total,
            status="ACCEPTED",
            valid_until=now() + timedelta(days=7),
            created_at=now() - timedelta(days=2),
        )
        session.add(q)
        session.flush()
        for name, price, qty in items:
            session.add(
                QuoteItem(
                    id=uuid.uuid4(),
                    quote_id=q.id,
                    item_name=name,
                    unit_price=float(price),
                    quantity=qty,
                    total_price=float(price * qty),
                )
            )
        session.flush()
        return q

    if appt1:
        create_quote_if_not_exists(
            appt1,
            [
                ("Màn hình iPhone 13 AMOLED", 1_800_000, 1),
                ("Pin iPhone 13 dung lượng cao", 350_000, 1),
            ],
        )

    if appt4:
        create_quote_if_not_exists(
            appt4,
            [
                ("Pin Xiaomi 12 gốc", 320_000, 1),
                ("Phí vệ sinh máy", 150_000, 1),
            ],
        )
    logger.info("✔ Quotes seeded")

    # =========================================================================
    # 9. INVOICES + PAYMENTS (chỉ cho COMPLETED appointments)
    # =========================================================================
    inv_counter = [1]

    def make_inv_number() -> str:
        n = f"INV-2026-{inv_counter[0]:04d}"
        inv_counter[0] += 1
        return n

    def make_pay_number() -> str:
        n = f"PAY-2026-{inv_counter[0]:04d}"
        inv_counter[0] += 1
        return n

    def create_invoice_if_not_exists(appt: Appointment, customer: Customer) -> None:
        existing = session.exec(
            select(Invoice).where(Invoice.appointment_id == appt.id)
        ).first()
        if existing:
            return
        inv = Invoice(
            id=uuid.uuid4(),
            invoice_number=make_inv_number(),
            appointment_id=appt.id,
            customer_id=customer.id,
            subtotal=appt.total_amount,
            discount_amount=0.0,
            tax_amount=0.0,
            total_amount=appt.total_amount,
            status="PAID",
            issue_date=now() - timedelta(days=1),
            created_at=now() - timedelta(days=1),
        )
        session.add(inv)
        session.flush()
        session.add(
            InvoiceItem(
                id=uuid.uuid4(),
                invoice_id=inv.id,
                item_name="Tổng dịch vụ sửa chữa",
                unit_price=appt.total_amount,
                quantity=1,
                total_price=appt.total_amount,
            )
        )
        session.add(
            Payment(
                id=uuid.uuid4(),
                payment_number=make_pay_number(),
                invoice_id=inv.id,
                amount=appt.total_amount,
                payment_method="CASH",
                payment_status="SUCCESS",
                paid_at=now() - timedelta(hours=2),
                notes="Thanh toán tiền mặt tại quầy",
                created_at=now() - timedelta(hours=2),
            )
        )
        session.flush()

    if appt1:
        create_invoice_if_not_exists(appt1, cust1)
    if appt4:
        create_invoice_if_not_exists(appt4, cust3)
    logger.info("✔ Invoices & Payments seeded")

    # =========================================================================
    # 10. REVIEWS (chỉ cho COMPLETED)
    # =========================================================================
    def create_review_if_not_exists(
        appt: Appointment,
        customer: Customer,
        tech: Technician,
        rating: int,
        comment: str,
    ) -> None:
        existing = session.exec(
            select(Review).where(Review.appointment_id == appt.id)
        ).first()
        if existing:
            return
        session.add(
            Review(
                id=uuid.uuid4(),
                appointment_id=appt.id,
                customer_id=customer.id,
                technician_id=tech.id,
                rating=rating,
                comment=comment,
                created_at=now(),
            )
        )
        session.flush()

    if appt1:
        create_review_if_not_exists(
            appt1, cust1, tech1, 5, "Sửa nhanh, làm tốt, giá hợp lý. Rất hài lòng!"
        )
    if appt4:
        create_review_if_not_exists(
            appt4,
            cust3,
            tech2,
            4,
            "Kỹ thuật viên nhiệt tình, máy sau khi sửa chạy tốt hơn nhiều.",
        )
    logger.info("✔ Reviews seeded")

    # =========================================================================
    # 11. NOTIFICATIONS
    # =========================================================================
    notif_data = [
        (
            cust1,
            "Lịch hẹn xác nhận",
            "Lịch hẹn APPT-2026-0001 của bạn đã được xác nhận.",
            "APPOINTMENT_REMINDER",
        ),
        (
            cust1,
            "Máy đã sửa xong",
            "iPhone 13 của bạn đã sửa xong. Vui lòng đến nhận máy.",
            "STATUS_UPDATE",
        ),
        (
            cust2,
            "Lịch hẹn sắp tới",
            "Bạn có lịch hẹn APPT-2026-0003 vào ngày mai.",
            "APPOINTMENT_REMINDER",
        ),
        (
            cust3,
            "Thanh toán thành công",
            "Hóa đơn INV-2026-0001 đã được thanh toán thành công.",
            "PAYMENT_CONFIRMATION",
        ),
    ]
    for customer, title, message, ntype in notif_data:
        session.add(
            Notification(
                id=uuid.uuid4(),
                customer_id=customer.id,
                title=title,
                message=message,
                notification_type=ntype,
                is_read=False,
                created_at=now(),
            )
        )
    session.flush()
    logger.info("✔ Notifications seeded")

    session.commit()
    logger.info("🎉 Seed hoàn tất – Database sẵn sàng demo!")


def main() -> None:
    setup_logging()
    logger.info("Bắt đầu seed DEMO data cho FixPhone...")
    with Session(engine) as session:
        seed(session)


if __name__ == "__main__":
    main()
