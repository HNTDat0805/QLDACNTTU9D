import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
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
    SystemLog,
    Technician,
    TechnicianSchedule,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)


def seed_all_data(session: Session) -> None:  # noqa: C901
    """
    Idempotent database seeding for FixPhone repair management system.
    Populates comprehensive test data across all tables and entities.
    """
    logger.info("Starting database seeding...")
    now = datetime.now(UTC)

    # =========================================================================
    # 1. USERS & SUPERUSER
    # =========================================================================
    users_to_create: list[dict[str, Any]] = [
        {
            "email": settings.FIRST_SUPERUSER,
            "full_name": "FixPhone System Admin",
            "role": UserRole.ADMIN.value,
            "is_superuser": True,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
        {
            "email": "manager@fixphone.vn",
            "full_name": "Nguyễn Quản Lý",
            "role": UserRole.MANAGER.value,
            "is_superuser": False,
            "password": "password123",
        },
        {
            "email": "staff@fixphone.vn",
            "full_name": "Trần Thị Lễ Tân",
            "role": UserRole.STAFF.value,
            "is_superuser": False,
            "password": "password123",
        },
        {
            "email": "tech.nguyen@fixphone.vn",
            "full_name": "Nguyễn Văn An",
            "role": UserRole.TECHNICIAN.value,
            "is_superuser": False,
            "password": "password123",
        },
        {
            "email": "tech.tran@fixphone.vn",
            "full_name": "Trần Minh Tuấn",
            "role": UserRole.TECHNICIAN.value,
            "is_superuser": False,
            "password": "password123",
        },
        {
            "email": "customer1@gmail.com",
            "full_name": "Lê Hoàng Long",
            "role": UserRole.CUSTOMER.value,
            "is_superuser": False,
            "password": "password123",
        },
        {
            "email": "customer2@gmail.com",
            "full_name": "Phạm Thu Hà",
            "role": UserRole.CUSTOMER.value,
            "is_superuser": False,
            "password": "password123",
        },
    ]

    users_map: dict[str, User] = {}
    for u_data in users_to_create:
        u_email = str(u_data["email"])
        u_full_name = str(u_data["full_name"])
        u_role = str(u_data["role"])
        u_is_superuser = bool(u_data["is_superuser"])
        u_password = str(u_data["password"])

        existing_user = session.exec(select(User).where(User.email == u_email)).first()
        if not existing_user:
            user_obj = User(
                email=u_email,
                full_name=u_full_name,
                role=u_role,
                is_superuser=u_is_superuser,
                is_active=True,
                hashed_password=get_password_hash(u_password),
            )
            session.add(user_obj)
            session.commit()
            session.refresh(user_obj)
            users_map[u_email] = user_obj
            logger.info("Created user: %s (%s)", user_obj.email, user_obj.role)
        else:
            if u_is_superuser and existing_user.role != UserRole.ADMIN.value:
                existing_user.role = UserRole.ADMIN.value
                if not existing_user.full_name:
                    existing_user.full_name = u_full_name
                session.add(existing_user)
                session.commit()
                session.refresh(existing_user)
            users_map[u_email] = existing_user

    admin_user = users_map[settings.FIRST_SUPERUSER]
    staff_user = users_map["staff@fixphone.vn"]
    tech_user_1 = users_map["tech.nguyen@fixphone.vn"]
    tech_user_2 = users_map["tech.tran@fixphone.vn"]
    cust_user_1 = users_map["customer1@gmail.com"]
    cust_user_2 = users_map["customer2@gmail.com"]

    # =========================================================================
    # 3. SERVICES (Dịch vụ sửa chữa)
    # =========================================================================
    services_to_create = [
        Service(
            name="Thay màn hình iPhone 14 Pro Max chính hãng",
            description="Màn hình Super Retina XDR OLED zin bóc máy, hiển thị 120Hz mượt mà, bảo hành 6 tháng",
            base_price=6500000.0,
            estimated_duration_minutes=60,
            is_active=True,
        ),
        Service(
            name="Ép kính màn hình iPhone 14 Pro Max",
            description="Ép kính cường lực Zin liền ron, giữ nguyên màn hình và cảm ứng gốc",
            base_price=1200000.0,
            estimated_duration_minutes=90,
            is_active=True,
        ),
        Service(
            name="Thay pin Pisen iPhone 11 dung lượng chuẩn",
            description="Pin Pisen chính hãng kèm tem bảo hiểm cháy nổ, bảo hành 12 tháng 1 đổi 1",
            base_price=650000.0,
            estimated_duration_minutes=30,
            is_active=True,
        ),
        Service(
            name="Thay cụm cổng sạc Type-C Samsung Galaxy S23 Ultra",
            description="Thay bo sạc zin tích hợp micro và IC sạc nhanh Super Fast Charging",
            base_price=850000.0,
            estimated_duration_minutes=45,
            is_active=True,
        ),
        Service(
            name="Vệ sinh & sấy khô máy vô nước chuyên sâu",
            description="Tháo chi tiết bo mạch, sấy bằng dung dịch chuyên dụng, quét sạch oxy hóa và đo chạm chập",
            base_price=250000.0,
            estimated_duration_minutes=45,
            is_active=True,
        ),
        Service(
            name="Thay cụm camera sau Xiaomi 13 Pro (Leica)",
            description="Cụm ống kính và cảm biến 1-inch Sony IMX989 zin bóc máy",
            base_price=1800000.0,
            estimated_duration_minutes=60,
            is_active=True,
        ),
        Service(
            name="Thay pin dung lượng cao iPad Air 5",
            description="Pin đạt chuẩn Apple, dung lượng 7606 mAh, bảo hành 6 tháng",
            base_price=1100000.0,
            estimated_duration_minutes=60,
            is_active=True,
        ),
        Service(
            name="Dán cường lực KingKong cao cấp",
            description="Kính cường lực vát cạnh 9D chống bám vân tay, độ trong suốt chuẩn HD",
            base_price=150000.0,
            estimated_duration_minutes=10,
            is_active=True,
        ),
    ]

    services_map: dict[str, Service] = {}
    for srv in services_to_create:
        existing_srv = session.exec(
            select(Service).where(Service.name == srv.name)
        ).first()
        if not existing_srv:
            session.add(srv)
            session.commit()
            session.refresh(srv)
            services_map[srv.name] = srv
        else:
            services_map[srv.name] = existing_srv

    # =========================================================================
    # 4. TECHNICIANS (Kỹ thuật viên)
    # =========================================================================
    techs_to_create = [
        Technician(
            user_id=tech_user_1.id,
            full_name="Nguyễn Văn An",
            phone_number="0901234567",
            specialization="Chuyên phần cứng Apple (iPhone/iPad), ép kính màn hình cong & OLED",
            is_active=True,
        ),
        Technician(
            user_id=tech_user_2.id,
            full_name="Trần Minh Tuấn",
            phone_number="0907654321",
            specialization="Chuyên sửa chữa Android, Samsung, Xiaomi, đo mạch vi IC nguồn",
            is_active=True,
        ),
        Technician(
            user_id=None,
            full_name="Vũ Quốc Đạt",
            phone_number="0988776655",
            specialization="Thay thế linh kiện nhanh, thay pin, dán màn hình lấy liền",
            is_active=True,
        ),
    ]

    techs_map: dict[str, Technician] = {}
    for tech_obj in techs_to_create:
        existing_tech = session.exec(
            select(Technician).where(Technician.phone_number == tech_obj.phone_number)
        ).first()
        if not existing_tech:
            session.add(tech_obj)
            session.commit()
            session.refresh(tech_obj)
            if tech_obj.phone_number:
                techs_map[tech_obj.phone_number] = tech_obj
        else:
            if existing_tech.phone_number:
                techs_map[existing_tech.phone_number] = existing_tech

    tech_an = techs_map["0901234567"]
    tech_tuan = techs_map["0907654321"]
    tech_dat = techs_map["0988776655"]

    # =========================================================================
    # 5. TECHNICIAN SCHEDULES (Lịch trực / làm việc)
    # =========================================================================
    today = date.today()
    for day_offset in range(3):
        work_day = today + timedelta(days=day_offset)
        for tech in [tech_an, tech_tuan, tech_dat]:
            existing_sched = session.exec(
                select(TechnicianSchedule).where(
                    TechnicianSchedule.technician_id == tech.id,
                    TechnicianSchedule.work_date == work_day,
                )
            ).first()
            if not existing_sched:
                sched = TechnicianSchedule(
                    technician_id=tech.id,
                    work_date=work_day,
                    start_time=time(8, 30),
                    end_time=time(17, 30),
                    status="AVAILABLE",
                    notes="Ca hành chính tại cửa hàng",
                )
                session.add(sched)
    session.commit()

    # =========================================================================
    # 6. CUSTOMERS (Khách hàng)
    # =========================================================================
    customers_to_create = [
        Customer(
            user_id=cust_user_1.id,
            full_name="Lê Hoàng Long",
            phone_number="0912345678",
            email="customer1@gmail.com",
            address="123 Nguyễn Thị Minh Khai, Phường Bến Thành, Quận 1, TP.HCM",
        ),
        Customer(
            user_id=cust_user_2.id,
            full_name="Phạm Thu Hà",
            phone_number="0934567890",
            email="customer2@gmail.com",
            address="456 Lê Văn Sỹ, Phường 14, Quận 3, TP.HCM",
        ),
        Customer(
            user_id=None,
            full_name="Nguyễn Hoàng Nam",
            phone_number="0987654321",
            email="nam.nguyen@gmail.com",
            address="789 Cách Mạng Tháng 8, Phường 5, Quận 10, TP.HCM",
        ),
        Customer(
            user_id=None,
            full_name="Đỗ Thị Mai",
            phone_number="0909112233",
            email="mai.do@gmail.com",
            address="12 Hoàng Hoa Thám, Phường 12, Quận Tân Bình, TP.HCM",
        ),
    ]

    customers_map: dict[str, Customer] = {}
    for c_obj in customers_to_create:
        existing_cust = session.exec(
            select(Customer).where(Customer.phone_number == c_obj.phone_number)
        ).first()
        if not existing_cust:
            session.add(c_obj)
            session.commit()
            session.refresh(c_obj)
            customers_map[c_obj.phone_number] = c_obj
        else:
            customers_map[c_obj.phone_number] = existing_cust

    cust_long = customers_map["0912345678"]
    cust_ha = customers_map["0934567890"]
    cust_nam = customers_map["0987654321"]
    cust_mai = customers_map["0909112233"]

    # =========================================================================
    # 7. DEVICES (Thiết bị của khách hàng)
    # =========================================================================
    devices_to_create = [
        Device(
            customer_id=cust_long.id,
            device_type="Smartphone",
            brand="Apple",
            model="iPhone 14 Pro Max",
            serial_number="F2LJK987KL",
            imei="356789123456781",
            color="Deep Purple",
            notes="Màn hình nứt kính góc trên bên phải, cảm ứng bình thường",
        ),
        Device(
            customer_id=cust_long.id,
            device_type="Tablet",
            brand="Apple",
            model="iPad Air 5",
            serial_number="DNPJ1234AB",
            imei=None,
            color="Space Gray",
            notes="Pin chai nhanh, tụt nguồn đột ngột khi dưới 20%",
        ),
        Device(
            customer_id=cust_ha.id,
            device_type="Smartphone",
            brand="Samsung",
            model="Galaxy S23 Ultra",
            serial_number="R5CT9012XYZ",
            imei="359876543210982",
            color="Phantom Black",
            notes="Cắm cáp sạc lúc nhận lúc không, nghi chân sạc lỏng",
        ),
        Device(
            customer_id=cust_nam.id,
            device_type="Smartphone",
            brand="Xiaomi",
            model="Xiaomi 13 Pro",
            serial_number="XM13P45678",
            imei="865432109876543",
            color="Ceramic White",
            notes="Rơi nứt kính lưng và kính camera sau làm mờ ảnh chụp",
        ),
        Device(
            customer_id=cust_mai.id,
            device_type="Smartphone",
            brand="Apple",
            model="iPhone 11",
            serial_number="C39DFG12AA",
            imei="353210987654321",
            color="Green",
            notes="Pin bảo trì còn 74%, cần thay pin dung lượng cao",
        ),
    ]

    devices_map: dict[str, Device] = {}
    for dev_obj in devices_to_create:
        existing_dev = session.exec(
            select(Device).where(
                Device.customer_id == dev_obj.customer_id,
                Device.model == dev_obj.model,
            )
        ).first()
        if not existing_dev:
            session.add(dev_obj)
            session.commit()
            session.refresh(dev_obj)
            devices_map[dev_obj.model] = dev_obj
        else:
            devices_map[dev_obj.model] = existing_dev

    dev_ip14 = devices_map["iPhone 14 Pro Max"]
    dev_s23 = devices_map["Galaxy S23 Ultra"]
    dev_xm13 = devices_map["Xiaomi 13 Pro"]
    dev_ip11 = devices_map["iPhone 11"]

    # =========================================================================
    # 8. APPOINTMENTS, SERVICES, STATUS HISTORY, QUOTES, INVOICES, PAYMENTS, REVIEWS
    # =========================================================================

    # --- Đơn 1: Hoàn thành & Đã thanh toán (APPT-2026-0001) ---
    appt1_num = "APPT-2026-0001"
    existing_appt1 = session.exec(
        select(Appointment).where(Appointment.appointment_number == appt1_num)
    ).first()
    if not existing_appt1:
        appt1 = Appointment(
            appointment_number=appt1_num,
            customer_id=cust_long.id,
            device_id=dev_ip14.id,
            technician_id=tech_an.id,
            appointment_date=now - timedelta(days=2),
            status="COMPLETED",
            customer_notes="Máy rơi vỡ mặt kính, mong shop giữ lại màn hình gốc",
            technician_diagnosis="Cảm ứng và phôi OLED hiển thị tốt, tiến hành tách ép kính mới và dán cường lực",
            estimated_completion_date=now - timedelta(days=2, hours=-2),
            actual_completion_date=now - timedelta(days=2, hours=-2),
            total_amount=1350000.0,
        )
        session.add(appt1)
        session.commit()
        session.refresh(appt1)

        # Gắn dịch vụ đơn 1
        srv_epkinh = services_map["Ép kính màn hình iPhone 14 Pro Max"]
        srv_dancl = services_map["Dán cường lực KingKong cao cấp"]
        session.add(
            AppointmentService(
                appointment_id=appt1.id,
                service_id=srv_epkinh.id,
                price_at_booking=srv_epkinh.base_price,
                quantity=1,
            )
        )
        session.add(
            AppointmentService(
                appointment_id=appt1.id,
                service_id=srv_dancl.id,
                price_at_booking=srv_dancl.base_price,
                quantity=1,
            )
        )

        # Lịch sử trạng thái đơn 1
        session.add(
            RepairStatusHistory(
                appointment_id=appt1.id,
                changed_by_user_id=staff_user.id,
                previous_status=None,
                new_status="PENDING",
                note="Tiếp nhận thiết bị tại quầy",
                created_at=now - timedelta(days=2, hours=3),
            )
        )
        session.add(
            RepairStatusHistory(
                appointment_id=appt1.id,
                changed_by_user_id=tech_an.user_id,
                previous_status="PENDING",
                new_status="IN_PROGRESS",
                note="Bắt đầu cắt kính vỡ và ép kính chân không",
                created_at=now - timedelta(days=2, hours=2),
            )
        )
        session.add(
            RepairStatusHistory(
                appointment_id=appt1.id,
                changed_by_user_id=tech_an.user_id,
                previous_status="IN_PROGRESS",
                new_status="COMPLETED",
                note="Đã kiểm tra cảm ứng hoàn hảo, vệ sinh và dán cường lực sẵn sàng giao",
                created_at=now - timedelta(days=2),
            )
        )

        # Báo giá đơn 1
        quo1 = Quote(
            quote_number="QUO-2026-0001",
            appointment_id=appt1.id,
            total_amount=1350000.0,
            status="ACCEPTED",
            valid_until=now + timedelta(days=5),
            customer_notes="Khách hàng đồng ý ép kính và dán thêm cường lực",
        )
        session.add(quo1)
        session.commit()
        session.refresh(quo1)

        session.add(
            QuoteItem(
                quote_id=quo1.id,
                service_id=srv_epkinh.id,
                item_name=srv_epkinh.name,
                unit_price=1200000.0,
                quantity=1,
                total_price=1200000.0,
            )
        )
        session.add(
            QuoteItem(
                quote_id=quo1.id,
                service_id=srv_dancl.id,
                item_name=srv_dancl.name,
                unit_price=150000.0,
                quantity=1,
                total_price=150000.0,
            )
        )

        # Hóa đơn đơn 1
        inv1 = Invoice(
            invoice_number="INV-2026-0001",
            appointment_id=appt1.id,
            customer_id=cust_long.id,
            subtotal=1350000.0,
            discount_amount=0.0,
            tax_amount=0.0,
            total_amount=1350000.0,
            status="PAID",
            notes="Đã thanh toán đủ qua ví MoMo",
        )
        session.add(inv1)
        session.commit()
        session.refresh(inv1)

        session.add(
            InvoiceItem(
                invoice_id=inv1.id,
                item_name=srv_epkinh.name,
                unit_price=1200000.0,
                quantity=1,
                total_price=1200000.0,
            )
        )
        session.add(
            InvoiceItem(
                invoice_id=inv1.id,
                item_name=srv_dancl.name,
                unit_price=150000.0,
                quantity=1,
                total_price=150000.0,
            )
        )

        # Thanh toán đơn 1
        session.add(
            Payment(
                payment_number="PAY-2026-0001",
                invoice_id=inv1.id,
                amount=1350000.0,
                payment_method="MOMO",
                payment_status="SUCCESS",
                transaction_reference="MOMO_TXN_9876543210",
                notes="Thanh toán qua quét mã QR MoMo tại quầy",
            )
        )

        # Đánh giá đơn 1
        session.add(
            Review(
                appointment_id=appt1.id,
                customer_id=cust_long.id,
                technician_id=tech_an.id,
                rating=5,
                comment="Kỹ thuật viên An làm rất nhanh và cẩn thận, màn hình ép xong trong vắt không một hạt bụi!",
            )
        )
        session.commit()

    # --- Đơn 2: Đang sửa chữa (APPT-2026-0002) ---
    appt2_num = "APPT-2026-0002"
    existing_appt2 = session.exec(
        select(Appointment).where(Appointment.appointment_number == appt2_num)
    ).first()
    if not existing_appt2:
        srv_s23 = services_map["Thay cụm cổng sạc Type-C Samsung Galaxy S23 Ultra"]
        appt2 = Appointment(
            appointment_number=appt2_num,
            customer_id=cust_ha.id,
            device_id=dev_s23.id,
            technician_id=tech_tuan.id,
            appointment_date=now - timedelta(hours=4),
            status="IN_PROGRESS",
            customer_notes="Máy không nhận sạc nhanh, cắm lúc vào lúc không",
            technician_diagnosis="Chân tiếp xúc cổng Type-C bị gãy chân và oxy hóa, cần thay cụm bo sạc mới",
            estimated_completion_date=now + timedelta(hours=2),
            total_amount=850000.0,
        )
        session.add(appt2)
        session.commit()
        session.refresh(appt2)

        session.add(
            AppointmentService(
                appointment_id=appt2.id,
                service_id=srv_s23.id,
                price_at_booking=srv_s23.base_price,
                quantity=1,
            )
        )

        session.add(
            RepairStatusHistory(
                appointment_id=appt2.id,
                changed_by_user_id=staff_user.id,
                previous_status=None,
                new_status="PENDING",
                note="Nhận máy kiểm tra",
                created_at=now - timedelta(hours=4),
            )
        )
        session.add(
            RepairStatusHistory(
                appointment_id=appt2.id,
                changed_by_user_id=tech_tuan.user_id,
                previous_status="PENDING",
                new_status="IN_PROGRESS",
                note="Đang tiến hành tháo máy và thay cụm bo sạc",
                created_at=now - timedelta(hours=1),
            )
        )

        quo2 = Quote(
            quote_number="QUO-2026-0002",
            appointment_id=appt2.id,
            total_amount=850000.0,
            status="ACCEPTED",
            valid_until=now + timedelta(days=3),
            customer_notes="Khách đã chốt giá qua điện thoại",
        )
        session.add(quo2)
        session.commit()
        session.refresh(quo2)

        session.add(
            QuoteItem(
                quote_id=quo2.id,
                service_id=srv_s23.id,
                item_name=srv_s23.name,
                unit_price=850000.0,
                quantity=1,
                total_price=850000.0,
            )
        )

        # Hóa đơn đang chờ thanh toán
        inv2 = Invoice(
            invoice_number="INV-2026-0002",
            appointment_id=appt2.id,
            customer_id=cust_ha.id,
            subtotal=850000.0,
            discount_amount=0.0,
            tax_amount=0.0,
            total_amount=850000.0,
            status="UNPAID",
            notes="Khách hàng sẽ thanh toán khi nhận máy",
        )
        session.add(inv2)
        session.commit()

    # --- Đơn 3: Chờ báo giá / duyệt (APPT-2026-0003) ---
    appt3_num = "APPT-2026-0003"
    existing_appt3 = session.exec(
        select(Appointment).where(Appointment.appointment_number == appt3_num)
    ).first()
    if not existing_appt3:
        srv_xm = services_map["Thay cụm camera sau Xiaomi 13 Pro (Leica)"]
        appt3 = Appointment(
            appointment_number=appt3_num,
            customer_id=cust_nam.id,
            device_id=dev_xm13.id,
            technician_id=tech_tuan.id,
            appointment_date=now - timedelta(hours=2),
            status="PENDING",
            customer_notes="Máy chụp ảnh bị đục mờ sau khi rơi nứt kính cam",
            technician_diagnosis="Cảm biến quang học bị bụi và trầy thấu kính, cần thay cụm cam sau chính hãng",
            total_amount=1800000.0,
        )
        session.add(appt3)
        session.commit()
        session.refresh(appt3)

        session.add(
            AppointmentService(
                appointment_id=appt3.id,
                service_id=srv_xm.id,
                price_at_booking=srv_xm.base_price,
                quantity=1,
            )
        )

        session.add(
            RepairStatusHistory(
                appointment_id=appt3.id,
                changed_by_user_id=staff_user.id,
                previous_status=None,
                new_status="PENDING",
                note="Tiếp nhận thiết bị, gửi báo giá",
                created_at=now - timedelta(hours=2),
            )
        )

        quo3 = Quote(
            quote_number="QUO-2026-0003",
            appointment_id=appt3.id,
            total_amount=1800000.0,
            status="SENT",
            valid_until=now + timedelta(days=2),
            customer_notes="Đã gửi tin nhắn báo giá cho anh Nam, đang chờ duyệt",
        )
        session.add(quo3)
        session.commit()
        session.refresh(quo3)

        session.add(
            QuoteItem(
                quote_id=quo3.id,
                service_id=srv_xm.id,
                item_name=srv_xm.name,
                unit_price=1800000.0,
                quantity=1,
                total_price=1800000.0,
            )
        )
        session.commit()

    # --- Đơn 4: Thay pin lấy liền đã hoàn tất (APPT-2026-0004) ---
    appt4_num = "APPT-2026-0004"
    existing_appt4 = session.exec(
        select(Appointment).where(Appointment.appointment_number == appt4_num)
    ).first()
    if not existing_appt4:
        srv_pin11 = services_map["Thay pin Pisen iPhone 11 dung lượng chuẩn"]
        srv_vesinh = services_map["Vệ sinh & sấy khô máy vô nước chuyên sâu"]
        appt4 = Appointment(
            appointment_number=appt4_num,
            customer_id=cust_mai.id,
            device_id=dev_ip11.id,
            technician_id=tech_dat.id,
            appointment_date=now - timedelta(days=1),
            status="COMPLETED",
            customer_notes="Pin chai 74%, yêu cầu thay pin lấy ngay",
            technician_diagnosis="Thay pin Pisen mới 100%, bảo trì hệ thống và vệ sinh màng loa",
            actual_completion_date=now - timedelta(days=1, hours=-1),
            total_amount=900000.0,
        )
        session.add(appt4)
        session.commit()
        session.refresh(appt4)

        session.add(
            AppointmentService(
                appointment_id=appt4.id,
                service_id=srv_pin11.id,
                price_at_booking=srv_pin11.base_price,
                quantity=1,
            )
        )
        session.add(
            AppointmentService(
                appointment_id=appt4.id,
                service_id=srv_vesinh.id,
                price_at_booking=srv_vesinh.base_price,
                quantity=1,
            )
        )

        session.add(
            RepairStatusHistory(
                appointment_id=appt4.id,
                changed_by_user_id=tech_dat.user_id,
                previous_status="PENDING",
                new_status="COMPLETED",
                note="Thay pin xong trong 25 phút, bàn giao máy tại quầy",
                created_at=now - timedelta(days=1),
            )
        )

        inv4 = Invoice(
            invoice_number="INV-2026-0004",
            appointment_id=appt4.id,
            customer_id=cust_mai.id,
            subtotal=900000.0,
            discount_amount=0.0,
            tax_amount=0.0,
            total_amount=900000.0,
            status="PAID",
            notes="Khách thanh toán tiền mặt",
        )
        session.add(inv4)
        session.commit()
        session.refresh(inv4)

        session.add(
            InvoiceItem(
                invoice_id=inv4.id,
                item_name=srv_pin11.name,
                unit_price=650000.0,
                quantity=1,
                total_price=650000.0,
            )
        )
        session.add(
            InvoiceItem(
                invoice_id=inv4.id,
                item_name=srv_vesinh.name,
                unit_price=250000.0,
                quantity=1,
                total_price=250000.0,
            )
        )

        session.add(
            Payment(
                payment_number="PAY-2026-0004",
                invoice_id=inv4.id,
                amount=900000.0,
                payment_method="CASH",
                payment_status="SUCCESS",
                notes="Thanh toán tiền mặt tại quầy lễ tân",
            )
        )

        session.add(
            Review(
                appointment_id=appt4.id,
                customer_id=cust_mai.id,
                technician_id=tech_dat.id,
                rating=5,
                comment="Kỹ thuật viên nhiệt tình, thay pin nhanh gọn trong 20 phút, máy dùng mát và pin rất trâu!",
            )
        )
        session.commit()

    # =========================================================================
    # 9. NOTIFICATIONS (Thông báo hệ thống)
    # =========================================================================
    notifications_to_create = [
        Notification(
            customer_id=cust_long.id,
            user_id=cust_user_1.id,
            title="Đơn sửa chữa hoàn thành 🎉",
            message="Thiết bị iPhone 14 Pro Max (APPT-2026-0001) đã được ép kính thành công. Mời bạn đến cửa hàng nhận máy!",
            notification_type="STATUS_UPDATE",
            is_read=True,
        ),
        Notification(
            customer_id=cust_long.id,
            user_id=cust_user_1.id,
            title="Xác nhận thanh toán thành công",
            message="Hóa đơn INV-2026-0001 trị giá 1.350.000 VNĐ đã được thanh toán thành công qua MoMo. Cảm ơn quý khách!",
            notification_type="PAYMENT_CONFIRMATION",
            is_read=True,
        ),
        Notification(
            customer_id=cust_ha.id,
            user_id=cust_user_2.id,
            title="Thiết bị đang được sửa chữa 🛠️",
            message="Kỹ thuật viên Trần Minh Tuấn đang tiến hành sửa chữa cụm chân sạc cho máy Galaxy S23 Ultra của bạn.",
            notification_type="STATUS_UPDATE",
            is_read=False,
        ),
        Notification(
            customer_id=None,
            user_id=admin_user.id,
            title="Cảnh báo linh kiện sắp hết",
            message="Màn hình chính hãng iPhone 14 Pro Max trong kho chỉ còn 2 chiếc. Vui lòng nhập thêm hàng.",
            notification_type="STATUS_UPDATE",
            is_read=False,
        ),
    ]

    for notif_obj in notifications_to_create:
        existing_notif = session.exec(
            select(Notification).where(
                Notification.title == notif_obj.title,
                Notification.message == notif_obj.message,
            )
        ).first()
        if not existing_notif:
            session.add(notif_obj)
    session.commit()

    # =========================================================================
    # 10. SYSTEM LOGS (Nhật ký kiểm toán)
    # =========================================================================
    logs_to_create = [
        SystemLog(
            user_id=admin_user.id,
            action="SYSTEM_INIT",
            entity_name="Database",
            entity_id="seed",
            details="Khởi tạo dữ liệu mẫu FixPhone ban đầu",
            ip_address="127.0.0.1",
        ),
        SystemLog(
            user_id=staff_user.id,
            action="CREATE_APPOINTMENT",
            entity_name="Appointment",
            entity_id=appt1_num,
            details="Lễ tân tiếp nhận đơn sửa chữa APPT-2026-0001 tại quầy",
            ip_address="192.168.1.10",
        ),
        SystemLog(
            user_id=tech_an.user_id,
            action="UPDATE_STATUS",
            entity_name="Appointment",
            entity_id=appt1_num,
            details="Kỹ thuật viên cập nhật trạng thái sang COMPLETED",
            ip_address="192.168.1.15",
        ),
        SystemLog(
            user_id=staff_user.id,
            action="PROCESS_PAYMENT",
            entity_name="Payment",
            entity_id="PAY-2026-0001",
            details="Thu ngân xác nhận thanh toán MoMo số tiền 1.350.000 VNĐ",
            ip_address="192.168.1.10",
        ),
    ]

    for log_obj in logs_to_create:
        existing_log = session.exec(
            select(SystemLog).where(
                SystemLog.action == log_obj.action,
                SystemLog.entity_id == log_obj.entity_id,
            )
        ).first()
        if not existing_log:
            session.add(log_obj)
    session.commit()

    logger.info("Successfully seeded all tables and entities for FixPhone!")
