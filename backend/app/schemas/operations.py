from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.entities import (
    InvoiceStatus,
    MachineStatus,
    OperationStatus,
    PaymentMethod,
    ScheduleStatus,
    WorkerStatus,
    UserRole,
)
from app.schemas.api import MaterialReferenceOut


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    role: UserRole


class AdminUserUpdate(BaseModel):
    role: UserRole
    is_active: bool
    password: str | None = Field(default=None, min_length=12, max_length=128)


class WorkerWrite(BaseModel):
    worker_code: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    skill: str | None = Field(default=None, max_length=160)
    status: WorkerStatus = WorkerStatus.ACTIVE
    user_id: int | None = None


class WorkerOut(WorkerWrite, ORMModel):
    id: int


class CustomerWrite(BaseModel):
    customer_code: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    shipping_address: str | None = None
    user_id: int | None = None


class CustomerOut(CustomerWrite, ORMModel):
    id: int


class ProductionLineWrite(BaseModel):
    line_code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    location: str | None = Field(default=None, max_length=160)
    is_active: bool = True


class ProductionLineOut(ProductionLineWrite, ORMModel):
    id: int


class MachineWrite(BaseModel):
    machine_code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    line_id: int | None = None
    status: MachineStatus = MachineStatus.AVAILABLE
    technical_notes: str | None = None


class MachineOut(MachineWrite, ORMModel):
    id: int


class ShiftWrite(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    start_time: time
    end_time: time
    is_active: bool = True

    @model_validator(mode="after")
    def require_nonzero_duration(self):
        if self.start_time == self.end_time:
            raise ValueError("Giờ bắt đầu và kết thúc ca không được trùng nhau.")
        return self


class ShiftOut(ShiftWrite, ORMModel):
    id: int


class ScheduleWrite(BaseModel):
    order_id: int
    worker_id: int
    machine_id: int
    line_id: int | None = None
    shift_id: int | None = None
    starts_at: datetime
    ends_at: datetime
    status: ScheduleStatus = ScheduleStatus.SCHEDULED
    notes: str | None = None

    @model_validator(mode="after")
    def validate_range(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Thời gian lịch phải kèm múi giờ.")
        if self.starts_at >= self.ends_at:
            raise ValueError("Thời gian kết thúc phải sau thời gian bắt đầu.")
        return self


class ScheduleOut(ORMModel):
    id: int
    order_id: int
    worker_id: int
    machine_id: int
    line_id: int | None
    shift_id: int | None
    starts_at: datetime
    ends_at: datetime
    status: ScheduleStatus
    notes: str | None
    created_by_id: int


class BOMWrite(BaseModel):
    product_name: str = Field(min_length=1, max_length=160)
    material_id: int
    quantity_per_unit: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    notes: str | None = None


class BOMOut(BOMWrite, ORMModel):
    id: int
    material: MaterialReferenceOut | None = None


class OperationWrite(BaseModel):
    order_id: int
    stage_name: str = Field(min_length=1, max_length=120)
    sequence: int = Field(gt=0)
    status: OperationStatus = OperationStatus.PLANNED
    completed_quantity: int = Field(default=0, ge=0)
    rejected_quantity: int = Field(default=0, ge=0)
    instructions: str | None = None


class OperationOut(OperationWrite, ORMModel):
    id: int


class ProductionLogWrite(BaseModel):
    order_id: int
    operation_id: int | None = None
    worker_id: int | None = None
    machine_id: int | None = None
    shift_id: int | None = None
    good_quantity: int = Field(default=0, ge=0)
    rejected_quantity: int = Field(default=0, ge=0)
    incident_type: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class ProductionLogOut(ProductionLogWrite, ORMModel):
    id: int
    logged_by_id: int
    logged_at: datetime


class DefectWrite(BaseModel):
    order_id: int
    operation_id: int | None = None
    quantity: int = Field(gt=0)
    defect_type: str = Field(min_length=1, max_length=120)
    description: str | None = None
    resolution: str | None = None


class DefectOut(DefectWrite, ORMModel):
    id: int
    reported_by_id: int
    reported_at: datetime


class InvoiceWrite(BaseModel):
    invoice_code: str = Field(min_length=1, max_length=40)
    order_id: int
    service_unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal(0), ge=0, max_digits=12, decimal_places=2)
    status: InvoiceStatus = InvoiceStatus.DRAFT


class InvoiceOut(ORMModel):
    id: int
    invoice_code: str
    order_id: int
    service_unit_price: Decimal
    discount_amount: Decimal
    subtotal: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    status: InvoiceStatus
    issued_at: datetime | None
    created_by_id: int


class PaymentWrite(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: PaymentMethod
    reference: str | None = Field(default=None, max_length=120)


class PaymentOut(PaymentWrite, ORMModel):
    id: int
    received_at: datetime
    received_by_id: int


class ExpenseWrite(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    category: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    order_id: int | None = None
    spent_at: datetime


class ExpenseOut(ExpenseWrite, ORMModel):
    id: int
    recorded_by_id: int


class FinancialReportOut(BaseModel):
    start_date: date | None
    end_date: date | None
    invoice_count: int
    billed_amount: Decimal
    collected_amount: Decimal
    outstanding_amount: Decimal
    expense_total: Decimal
    net_collected: Decimal


class AuditLogOut(ORMModel):
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    details: str | None
    created_at: datetime
