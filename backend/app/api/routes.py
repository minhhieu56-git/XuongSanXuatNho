from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession, ManagerUser
from app.core.security import create_access_token, verify_password
from app.models import InventoryItem, ProductionOrder, User
from app.models.entities import OrderStatus
from app.schemas.api import (
    AIAnalysisOut,
    AIAnalysisRequest,
    AIStatusOut,
    DashboardOut,
    InventoryCreate,
    InventoryOut,
    InventoryUpdate,
    LoginRequest,
    OrderCreate,
    OrderOut,
    OrderUpdate,
    TokenOut,
    UserOut,
)
from app.services.gemini import analyze_operations

router = APIRouter()


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginRequest, db: DbSession) -> TokenOut:
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không chính xác.")
    return TokenOut(access_token=create_access_token(str(user.id)), user=UserOut.model_validate(user))


@router.get("/auth/me", response_model=UserOut)
def get_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/inventory", response_model=list[InventoryOut])
def list_inventory(
    db: DbSession,
    user: CurrentUser,
    search: str = Query(default="", max_length=120),
    low_stock: bool = False,
    sort_by: str = Query(default="name", pattern="^(name|quantity|updated_at)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> list[InventoryItem]:
    del user
    query = select(InventoryItem)
    if search.strip():
        term = f"%{search.strip()}%"
        query = query.where(or_(InventoryItem.name.ilike(term), InventoryItem.sku.ilike(term)))
    if low_stock:
        query = query.where(InventoryItem.quantity <= InventoryItem.minimum_quantity)
    column = getattr(InventoryItem, sort_by)
    query = query.order_by(column.desc() if sort_order == "desc" else column.asc())
    return list(db.scalars(query).all())


@router.post("/inventory", response_model=InventoryOut, status_code=status.HTTP_201_CREATED)
def create_inventory(data: InventoryCreate, db: DbSession, user: ManagerUser) -> InventoryItem:
    del user
    item = InventoryItem(**data.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "SKU đã tồn tại hoặc dữ liệu tồn kho không hợp lệ.") from exc
    db.refresh(item)
    return item


@router.put("/inventory/{item_id}", response_model=InventoryOut)
def update_inventory(item_id: int, data: InventoryUpdate, db: DbSession, user: ManagerUser) -> InventoryItem:
    del user
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(404, "Không tìm thấy mặt hàng.")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "SKU đã tồn tại hoặc dữ liệu tồn kho không hợp lệ.") from exc
    db.refresh(item)
    return item


@router.delete("/inventory/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory(item_id: int, db: DbSession, user: ManagerUser) -> None:
    del user
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(404, "Không tìm thấy mặt hàng.")
    db.delete(item)
    db.commit()


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    db: DbSession,
    user: CurrentUser,
    search: str = Query(default="", max_length=120),
    order_status: OrderStatus | None = None,
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> list[ProductionOrder]:
    del user
    query = select(ProductionOrder)
    if search.strip():
        term = f"%{search.strip()}%"
        query = query.where(or_(ProductionOrder.order_code.ilike(term), ProductionOrder.product_name.ilike(term)))
    if order_status:
        query = query.where(ProductionOrder.status == order_status)
    query = query.order_by(
        ProductionOrder.created_at.desc() if sort_order == "desc" else ProductionOrder.created_at.asc()
    )
    return list(db.scalars(query).all())


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, db: DbSession, user: ManagerUser) -> ProductionOrder:
    if data.material_id is not None and db.get(InventoryItem, data.material_id) is None:
        raise HTTPException(422, "Nguyên vật liệu được chọn không tồn tại.")
    order = ProductionOrder(**data.model_dump(), created_by_id=user.id)
    db.add(order)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Mã đơn hàng đã tồn tại hoặc dữ liệu không hợp lệ.") from exc
    db.refresh(order)
    return order


@router.put("/orders/{order_id}", response_model=OrderOut)
def update_order(order_id: int, data: OrderUpdate, db: DbSession, user: ManagerUser) -> ProductionOrder:
    order = db.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(404, "Không tìm thấy đơn sản xuất.")
    if data.material_id is not None and db.get(InventoryItem, data.material_id) is None:
        raise HTTPException(422, "Nguyên vật liệu được chọn không tồn tại.")
    for key, value in data.model_dump().items():
        setattr(order, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Mã đơn hàng đã tồn tại hoặc dữ liệu không hợp lệ.") from exc
    db.refresh(order)
    return order


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: DbSession, user: ManagerUser) -> None:
    del user
    order = db.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(404, "Không tìm thấy đơn sản xuất.")
    db.delete(order)
    db.commit()


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: DbSession, user: CurrentUser) -> DashboardOut:
    del user
    order_count = db.scalar(select(func.count()).select_from(ProductionOrder)) or 0
    active_count = db.scalar(
        select(func.count()).select_from(ProductionOrder).where(ProductionOrder.status == OrderStatus.IN_PROGRESS)
    ) or 0
    completed_count = db.scalar(
        select(func.count()).select_from(ProductionOrder).where(ProductionOrder.status == OrderStatus.COMPLETED)
    ) or 0
    low_stock_count = db.scalar(
        select(func.count()).select_from(InventoryItem).where(InventoryItem.quantity <= InventoryItem.minimum_quantity)
    ) or 0
    inventory_value = db.scalar(select(func.sum(InventoryItem.quantity * InventoryItem.unit_cost))) or Decimal(0)
    recent_orders = list(
        db.scalars(select(ProductionOrder).order_by(ProductionOrder.created_at.desc()).limit(5)).all()
    )
    return DashboardOut(
        order_count=order_count,
        active_order_count=active_count,
        completed_order_count=completed_count,
        low_stock_count=low_stock_count,
        inventory_value=inventory_value,
        recent_orders=recent_orders,
    )


@router.post("/ai/analysis", response_model=AIAnalysisOut)
async def ai_analysis(data: AIAnalysisRequest, db: DbSession, user: CurrentUser) -> dict[str, object]:
    del user
    return await analyze_operations(db, data.question)


@router.get("/ai/status", response_model=AIStatusOut)
def ai_status(user: CurrentUser) -> AIStatusOut:
    del user
    if settings.gemini_api_key:
        return AIStatusOut(provider="gemini", model=settings.gemini_model)
    return AIStatusOut(provider="local", model="Phân tích quy tắc nội bộ")
