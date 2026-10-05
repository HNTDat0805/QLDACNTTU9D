"""Add FixPhone CSDL: customer, device, service, technician, appointment,
quote, invoice, payment, review, notification, system_log

Revision ID: a1b2c3d4e5f6
Revises: fe56fa70289e
Create Date: 2026-09-29 19:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =====================================================================
    # Modify User table: add 'role' column for FixPhone role-based access
    # =====================================================================
    op.add_column(
        "user",
        sa.Column("role", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default="customer"),
    )
    op.create_index("ix_user_role", "user", ["role"])

    # =====================================================================
    # CUSTOMER
    # =====================================================================
    op.create_table(
        "customer",
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("phone_number", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("address", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(phone_number) >= 8", name="check_customer_phone_min_length"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_number"),
    )
    op.create_index("ix_customer_phone_number", "customer", ["phone_number"], unique=True)
    op.create_index("ix_customer_user_id", "customer", ["user_id"])

    # =====================================================================
    # DEVICE
    # =====================================================================
    op.create_table(
        "device",
        sa.Column("device_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default="Smartphone"),
        sa.Column("brand", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("serial_number", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("imei", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("color", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_device_brand", "device", ["brand"])
    op.create_index("ix_device_model", "device", ["model"])
    op.create_index("ix_device_customer_id", "device", ["customer_id"])

    # =====================================================================
    # SERVICE
    # =====================================================================
    op.create_table(
        "service",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("base_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("base_price >= 0", name="check_service_base_price_non_negative"),
        sa.CheckConstraint("estimated_duration_minutes > 0", name="check_service_duration_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_service_name", "service", ["name"], unique=True)
    op.create_index("ix_service_is_active", "service", ["is_active"])

    # =====================================================================
    # TECHNICIAN
    # =====================================================================
    op.create_table(
        "technician",
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("phone_number", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column("specialization", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_number"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_technician_is_active", "technician", ["is_active"])
    op.create_index("ix_technician_user_id", "technician", ["user_id"])

    # =====================================================================
    # TECHNICIAN SCHEDULE
    # =====================================================================
    op.create_table(
        "technician_schedule",
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default="AVAILABLE"),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("technician_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("end_time > start_time", name="check_schedule_time_valid"),
        sa.ForeignKeyConstraint(["technician_id"], ["technician.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_technician_schedule_work_date", "technician_schedule", ["work_date"])
    op.create_index("ix_technician_schedule_technician_id", "technician_schedule", ["technician_id"])

    # =====================================================================
    # APPOINTMENT
    # =====================================================================
    op.create_table(
        "appointment",
        sa.Column("appointment_number", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("appointment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default="PENDING"),
        sa.Column("cancellation_reason", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("customer_notes", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("technician_diagnosis", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("estimated_completion_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_completion_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("technician_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("total_amount >= 0", name="check_appointment_total_amount_non_negative"),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["device_id"], ["device.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["technician_id"], ["technician.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_number"),
    )
    op.create_index("ix_appointment_appointment_number", "appointment", ["appointment_number"], unique=True)
    op.create_index("ix_appointment_appointment_date", "appointment", ["appointment_date"])
    op.create_index("ix_appointment_status", "appointment", ["status"])
    op.create_index("ix_appointment_customer_id", "appointment", ["customer_id"])
    op.create_index("ix_appointment_device_id", "appointment", ["device_id"])
    op.create_index("ix_appointment_technician_id", "appointment", ["technician_id"])

    # =====================================================================
    # APPOINTMENT SERVICE (Many-to-many junction + price snapshot)
    # =====================================================================
    op.create_table(
        "appointment_service",
        sa.Column("price_at_booking", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("price_at_booking >= 0", name="check_appointment_service_price_non_negative"),
        sa.CheckConstraint("quantity > 0", name="check_appointment_service_quantity_positive"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["service.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_appointment_service_appointment_id", "appointment_service", ["appointment_id"])
    op.create_index("ix_appointment_service_service_id", "appointment_service", ["service_id"])

    # =====================================================================
    # REPAIR STATUS HISTORY (Audit trail)
    # =====================================================================
    op.create_table(
        "repair_status_history",
        sa.Column("previous_status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("new_status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repair_status_history_appointment_id", "repair_status_history", ["appointment_id"])
    op.create_index("ix_repair_status_history_new_status", "repair_status_history", ["new_status"])
    op.create_index("ix_repair_status_history_created_at", "repair_status_history", ["created_at"])

    # =====================================================================
    # QUOTE
    # =====================================================================
    op.create_table(
        "quote",
        sa.Column("quote_number", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("customer_notes", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("total_amount >= 0", name="check_quote_total_amount_non_negative"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointment.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quote_number"),
    )
    op.create_index("ix_quote_quote_number", "quote", ["quote_number"], unique=True)
    op.create_index("ix_quote_status", "quote", ["status"])
    op.create_index("ix_quote_appointment_id", "quote", ["appointment_id"])

    # =====================================================================
    # QUOTE ITEM
    # =====================================================================
    op.create_table(
        "quote_item",
        sa.Column("item_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quote_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("unit_price >= 0", name="check_quote_item_unit_price_non_negative"),
        sa.CheckConstraint("quantity > 0", name="check_quote_item_quantity_positive"),
        sa.CheckConstraint("total_price >= 0", name="check_quote_item_total_price_non_negative"),
        sa.ForeignKeyConstraint(["quote_id"], ["quote.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["service.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_item_quote_id", "quote_item", ["quote_id"])

    # =====================================================================
    # INVOICE
    # =====================================================================
    op.create_table(
        "invoice",
        sa.Column("invoice_number", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("discount_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tax_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default="UNPAID"),
        sa.Column("issue_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("subtotal >= 0", name="check_invoice_subtotal_non_negative"),
        sa.CheckConstraint("discount_amount >= 0", name="check_invoice_discount_non_negative"),
        sa.CheckConstraint("tax_amount >= 0", name="check_invoice_tax_non_negative"),
        sa.CheckConstraint("total_amount >= 0", name="check_invoice_total_amount_non_negative"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointment.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_id"),
        sa.UniqueConstraint("invoice_number"),
    )
    op.create_index("ix_invoice_invoice_number", "invoice", ["invoice_number"], unique=True)
    op.create_index("ix_invoice_status", "invoice", ["status"])
    op.create_index("ix_invoice_appointment_id", "invoice", ["appointment_id"], unique=True)
    op.create_index("ix_invoice_customer_id", "invoice", ["customer_id"])

    # =====================================================================
    # INVOICE ITEM
    # =====================================================================
    op.create_table(
        "invoice_item",
        sa.Column("item_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("unit_price >= 0", name="check_invoice_item_unit_price_non_negative"),
        sa.CheckConstraint("quantity > 0", name="check_invoice_item_quantity_positive"),
        sa.CheckConstraint("total_price >= 0", name="check_invoice_item_total_price_non_negative"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoice.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_item_invoice_id", "invoice_item", ["invoice_id"])

    # =====================================================================
    # PAYMENT
    # =====================================================================
    op.create_table(
        "payment",
        sa.Column("payment_number", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("payment_method", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("payment_status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default="SUCCESS"),
        sa.Column("transaction_reference", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount > 0", name="check_payment_amount_positive"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoice.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_number"),
    )
    op.create_index("ix_payment_payment_number", "payment", ["payment_number"], unique=True)
    op.create_index("ix_payment_payment_status", "payment", ["payment_status"])
    op.create_index("ix_payment_invoice_id", "payment", ["invoice_id"])

    # =====================================================================
    # REVIEW
    # =====================================================================
    op.create_table(
        "review",
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("technician_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="check_review_rating_1_to_5"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointment.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["technician_id"], ["technician.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_id"),
    )
    op.create_index("ix_review_appointment_id", "review", ["appointment_id"], unique=True)
    op.create_index("ix_review_customer_id", "review", ["customer_id"])
    op.create_index("ix_review_technician_id", "review", ["technician_id"])

    # =====================================================================
    # NOTIFICATION
    # =====================================================================
    op.create_table(
        "notification",
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("message", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=False),
        sa.Column("notification_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default="STATUS_UPDATE"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_customer_id", "notification", ["customer_id"])
    op.create_index("ix_notification_user_id", "notification", ["user_id"])
    op.create_index("ix_notification_is_read", "notification", ["is_read"])
    op.create_index("ix_notification_created_at", "notification", ["created_at"])

    # =====================================================================
    # SYSTEM LOG
    # =====================================================================
    op.create_table(
        "system_log",
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("entity_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("entity_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("details", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column("ip_address", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_log_action", "system_log", ["action"])
    op.create_index("ix_system_log_user_id", "system_log", ["user_id"])
    op.create_index("ix_system_log_created_at", "system_log", ["created_at"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("system_log")
    op.drop_table("notification")
    op.drop_table("review")
    op.drop_table("payment")
    op.drop_table("invoice_item")
    op.drop_table("invoice")
    op.drop_table("quote_item")
    op.drop_table("quote")
    op.drop_table("repair_status_history")
    op.drop_table("appointment_service")
    op.drop_table("appointment")
    op.drop_table("technician_schedule")
    op.drop_table("technician")
    op.drop_table("service")
    op.drop_table("device")
    op.drop_table("customer")
    op.drop_index("ix_user_role", table_name="user")
    op.drop_column("user", "role")
