from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer

from app.models.entities import OrderStatus, UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class InventoryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    unit: str = Field(min_length=1, max_length=30)
    quantity: Decimal = Field(ge=0)
    minimum_quantity: Decimal = Field(ge=0)
    unit_cost: Decimal = Field(ge=0)


class InventoryUpdate(InventoryCreate):
    pass


class InventoryOut(InventoryCreate):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("quantity", "minimum_quantity", "unit_cost")
    def serialize_decimal(self, value: Decimal) -> float:
        return float(value)


class MaterialReferenceOut(BaseModel):
    id: int
    sku: str
    name: str
    unit: str

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    order_code: str = Field(min_length=1, max_length=40)
    product_name: str = Field(min_length=1, max_length=160)
    quantity: int = Field(gt=0, le=1_000_000)
    due_date: datetime | None = None
    status: OrderStatus = OrderStatus.PLANNED
    notes: str | None = Field(default=None, max_length=4000)
    material_id: int | None = None
    customer_id: int | None = None


class OrderUpdate(OrderCreate):
    pass


class OrderOut(OrderCreate):
    id: int
    created_by_id: int
    created_at: datetime
    material: MaterialReferenceOut | None = None

    model_config = ConfigDict(from_attributes=True)


class DashboardOut(BaseModel):
    order_count: int
    active_order_count: int
    completed_order_count: int
    low_stock_count: int
    inventory_value: Decimal
    recent_orders: list[OrderOut]

    @field_serializer("inventory_value")
    def serialize_inventory_value(self, value: Decimal) -> float:
        return float(value)


class AIAnalysisRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)


class AIShiftSummaryRequest(BaseModel):
    shift_id: int


class AICustomerProgressRequest(BaseModel):
    order_id: int


class AITechnicalExplanationRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=160)


class AIAnalysisOut(BaseModel):
    answer: str
    model: str
    provider: str
    generated_at: datetime
    data_scope: str


class AIStatusOut(BaseModel):
    provider: str
    model: str
