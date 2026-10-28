from datetime import datetime, time, timezone
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    WORKER = "worker"
    ACCOUNTANT = "accountant"
    CUSTOMER = "customer"


class OrderStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkerStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class MachineStatus(StrEnum):
    AVAILABLE = "available"
    OPERATING = "operating"
    MAINTENANCE = "maintenance"
    BROKEN = "broken"


class ScheduleStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OperationStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"


class PaymentMethod(StrEnum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.WORKER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    worker_profile: Mapped["Worker | None"] = relationship(back_populates="user", uselist=False)
    customer_profile: Mapped["Customer | None"] = relationship(back_populates="user", uselist=False)


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    skill: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[WorkerStatus] = mapped_column(
        Enum(WorkerStatus, name="worker_status"), default=WorkerStatus.ACTIVE, index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    user: Mapped[User | None] = relationship(back_populates="worker_profile")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shipping_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    user: Mapped[User | None] = relationship(back_populates="customer_profile")


class ProductionLine(Base):
    __tablename__ = "production_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    line_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    line_id: Mapped[int | None] = mapped_column(ForeignKey("production_lines.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[MachineStatus] = mapped_column(
        Enum(MachineStatus, name="machine_status"), default=MachineStatus.AVAILABLE, index=True
    )
    technical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    line: Mapped[ProductionLine | None] = relationship()


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProductionOrder(Base):
    __tablename__ = "production_orders"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    product_name: Mapped[str] = mapped_column(String(160), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), default=OrderStatus.PLANNED, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    material: Mapped["InventoryItem | None"] = relationship(back_populates="order_lines")
    customer: Mapped[Customer | None] = relationship()
    created_by: Mapped[User] = relationship()


class WorkSchedule(Base):
    __tablename__ = "work_schedules"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="ck_schedule_valid_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("production_orders.id", ondelete="CASCADE"), index=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="RESTRICT"), index=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id", ondelete="RESTRICT"), index=True)
    line_id: Mapped[int | None] = mapped_column(ForeignKey("production_lines.id", ondelete="SET NULL"), nullable=True)
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(ScheduleStatus, name="schedule_status"), default=ScheduleStatus.SCHEDULED, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    order: Mapped[ProductionOrder] = relationship()
    worker: Mapped[Worker] = relationship()
    machine: Mapped[Machine] = relationship()
    line: Mapped[ProductionLine | None] = relationship()
    shift: Mapped[Shift | None] = relationship()


class BOMItem(Base):
    __tablename__ = "bom_items"
    __table_args__ = (
        UniqueConstraint("product_name", "material_id", name="uq_bom_product_material"),
        CheckConstraint("quantity_per_unit > 0", name="ck_bom_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(String(160), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"), index=True)
    quantity_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    material: Mapped["InventoryItem"] = relationship()


class ProductionOperation(Base):
    __tablename__ = "production_operations"
    __table_args__ = (
        UniqueConstraint("order_id", "sequence", name="uq_operation_order_sequence"),
        CheckConstraint("sequence > 0", name="ck_operation_sequence_positive"),
        CheckConstraint("completed_quantity >= 0", name="ck_operation_completed_nonnegative"),
        CheckConstraint("rejected_quantity >= 0", name="ck_operation_rejected_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("production_orders.id", ondelete="CASCADE"), index=True)
    stage_name: Mapped[str] = mapped_column(String(120))
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus, name="operation_status"), default=OperationStatus.PLANNED, index=True
    )
    completed_quantity: Mapped[int] = mapped_column(Integer, default=0)
    rejected_quantity: Mapped[int] = mapped_column(Integer, default=0)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[ProductionOrder] = relationship()


class ProductionLog(Base):
    __tablename__ = "production_logs"
    __table_args__ = (
        CheckConstraint("good_quantity >= 0", name="ck_log_good_nonnegative"),
        CheckConstraint("rejected_quantity >= 0", name="ck_log_rejected_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("production_orders.id", ondelete="CASCADE"), index=True)
    operation_id: Mapped[int | None] = mapped_column(ForeignKey("production_operations.id", ondelete="SET NULL"), nullable=True)
    worker_id: Mapped[int | None] = mapped_column(ForeignKey("workers.id", ondelete="SET NULL"), nullable=True)
    machine_id: Mapped[int | None] = mapped_column(ForeignKey("machines.id", ondelete="SET NULL"), nullable=True)
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    good_quantity: Mapped[int] = mapped_column(Integer, default=0)
    rejected_quantity: Mapped[int] = mapped_column(Integer, default=0)
    incident_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    order: Mapped[ProductionOrder] = relationship()
    operation: Mapped[ProductionOperation | None] = relationship()
    worker: Mapped[Worker | None] = relationship()
    machine: Mapped[Machine | None] = relationship()


class QualityDefect(Base):
    __tablename__ = "quality_defects"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_defect_quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("production_orders.id", ondelete="CASCADE"), index=True)
    operation_id: Mapped[int | None] = mapped_column(ForeignKey("production_operations.id", ondelete="SET NULL"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    defect_type: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("service_unit_price >= 0", name="ck_invoice_unit_price_nonnegative"),
        CheckConstraint("discount_amount >= 0", name="ck_invoice_discount_nonnegative"),
        CheckConstraint("subtotal >= 0", name="ck_invoice_subtotal_nonnegative"),
        CheckConstraint("total_amount >= 0", name="ck_invoice_total_nonnegative"),
        CheckConstraint("amount_paid >= 0 AND amount_paid <= total_amount", name="ck_invoice_paid_in_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("production_orders.id", ondelete="RESTRICT"), unique=True, index=True)
    service_unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"), default=InvoiceStatus.DRAFT, index=True
    )
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    order: Mapped[ProductionOrder] = relationship()


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payment_amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"))
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    received_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_expense_amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    spent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    recorded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_inventory_quantity_nonnegative"),
        CheckConstraint("minimum_quantity >= 0", name="ck_inventory_minimum_nonnegative"),
        CheckConstraint("unit_cost >= 0", name="ck_inventory_cost_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    unit: Mapped[str] = mapped_column(String(30))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    minimum_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    order_lines: Mapped[list["ProductionOrder"]] = relationship(back_populates="material")
