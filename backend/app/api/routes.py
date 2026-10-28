from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.config import PROJECT_ROOT, settings
from app.core.deps import CurrentUser, DbSession, ManagerUser, ensure_roles
from app.core.security import create_access_token, hash_password, verify_password
from app.models import (
    AuditLog,
    BOMItem,
    Customer,
    InventoryItem,
    ProductionLog,
    ProductionOperation,
    ProductionOrder,
    Shift,
    User,
    WorkSchedule,
    Worker,
)
from app.models.entities import OrderStatus, UserRole
from app.schemas.api import (
    AIAnalysisOut,
    AIAnalysisRequest,
    ChangePasswordRequest,
    AIStatusOut,
    AIShiftSummaryRequest,
    AICustomerProgressRequest,
    AITechnicalExplanationRequest,
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
from app.services.gemini import analyze_operations, generate_ai_response

router = APIRouter()


def _record_change(db, user: User, action: str, entity: str, entity_id: int) -> None:
    db.add(AuditLog(user_id=user.id, action=action, entity_type=entity, entity_id=entity_id))


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginRequest, db: DbSession) -> TokenOut:
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not verify_password(data.password, user.password_hash) or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không chính xác.")
    return TokenOut(access_token=create_access_token(str(user.id)), user=UserOut.model_validate(user))


@router.get("/auth/me", response_model=UserOut)
def get_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/auth/change-password", status_code=204)
def change_password(data: ChangePasswordRequest, db: DbSession, user: CurrentUser) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(422, "Mật khẩu hiện tại không chính xác.")
    if data.current_password == data.new_password:
        raise HTTPException(422, "Mật khẩu mới phải khác mật khẩu hiện tại.")
    user.password_hash = hash_password(data.new_password)
    _record_change(db, user, "change_password", "user", user.id)
    db.commit()


@router.get("/inventory", response_model=list[InventoryOut])
def list_inventory(
    db: DbSession,
    user: CurrentUser,
    search: str = Query(default="", max_length=120),
    low_stock: bool = False,
    sort_by: str = Query(default="name", pattern="^(name|quantity|updated_at)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> list[InventoryItem]:
    ensure_roles(user, UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT)
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
    item = InventoryItem(**data.model_dump())
    db.add(item)
    try:
        db.flush()
        _record_change(db, user, "create", "inventory_item", item.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "SKU đã tồn tại hoặc dữ liệu tồn kho không hợp lệ.") from exc
    db.refresh(item)
    return item


@router.put("/inventory/{item_id}", response_model=InventoryOut)
def update_inventory(item_id: int, data: InventoryUpdate, db: DbSession, user: ManagerUser) -> InventoryItem:
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(404, "Không tìm thấy mặt hàng.")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    try:
        _record_change(db, user, "update", "inventory_item", item.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "SKU đã tồn tại hoặc dữ liệu tồn kho không hợp lệ.") from exc
    db.refresh(item)
    return item


@router.delete("/inventory/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory(item_id: int, db: DbSession, user: ManagerUser) -> None:
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(404, "Không tìm thấy mặt hàng.")
    db.delete(item)
    _record_change(db, user, "delete", "inventory_item", item_id)
    db.commit()


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    db: DbSession,
    user: CurrentUser,
    search: str = Query(default="", max_length=120),
    order_status: OrderStatus | None = None,
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> list[ProductionOrder]:
    query = select(ProductionOrder)
    if user.role == UserRole.CUSTOMER:
        customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
        query = query.where(ProductionOrder.customer_id == (customer.id if customer else -1))
    elif user.role == UserRole.WORKER:
        worker = db.scalar(select(Worker).where(Worker.user_id == user.id))
        query = query.join(WorkSchedule).where(
            WorkSchedule.worker_id == (worker.id if worker else -1)
        ).distinct()
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
def create_order(data: OrderCreate, db: DbSession, user: CurrentUser) -> ProductionOrder:
    if user.role == UserRole.CUSTOMER:
        customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
        if customer is None:
            raise HTTPException(403, "Tài khoản chưa được liên kết hồ sơ khách hàng.")
        data.customer_id = customer.id
        data.material_id = None
        data.status = OrderStatus.PLANNED
    elif user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(403, "Bạn không có quyền tạo đơn sản xuất.")
    if data.material_id is not None and db.get(InventoryItem, data.material_id) is None:
        raise HTTPException(422, "Nguyên vật liệu được chọn không tồn tại.")
    if data.customer_id is not None and db.get(Customer, data.customer_id) is None:
        raise HTTPException(422, "Khách hàng được chọn không tồn tại.")
    order = ProductionOrder(**data.model_dump(), created_by_id=user.id)
    db.add(order)
    try:
        db.flush()
        _record_change(db, user, "create", "production_order", order.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Mã đơn hàng đã tồn tại hoặc dữ liệu không hợp lệ.") from exc
    db.refresh(order)
    return order


@router.put("/orders/{order_id}", response_model=OrderOut)
def update_order(order_id: int, data: OrderUpdate, db: DbSession, user: CurrentUser) -> ProductionOrder:
    order = db.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(404, "Không tìm thấy đơn sản xuất.")
    if user.role == UserRole.CUSTOMER:
        customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
        if customer is None or order.customer_id != customer.id:
            raise HTTPException(404, "Không tìm thấy đơn sản xuất.")
        if order.status != OrderStatus.PLANNED or data.status not in (OrderStatus.PLANNED, OrderStatus.CANCELLED):
            raise HTTPException(409, "Chỉ có thể cập nhật hoặc hủy đơn hàng đang chờ xác nhận.")
        data.customer_id = customer.id
        data.material_id = None
        data.order_code = order.order_code
    elif user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(403, "Bạn không có quyền cập nhật đơn sản xuất.")
    if data.material_id is not None and db.get(InventoryItem, data.material_id) is None:
        raise HTTPException(422, "Nguyên vật liệu được chọn không tồn tại.")
    if data.customer_id is not None and db.get(Customer, data.customer_id) is None:
        raise HTTPException(422, "Khách hàng được chọn không tồn tại.")
    for key, value in data.model_dump().items():
        setattr(order, key, value)
    try:
        _record_change(db, user, "update", "production_order", order.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Mã đơn hàng đã tồn tại hoặc dữ liệu không hợp lệ.") from exc
    db.refresh(order)
    return order


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: DbSession, user: ManagerUser) -> None:
    order = db.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(404, "Không tìm thấy đơn sản xuất.")
    db.delete(order)
    _record_change(db, user, "delete", "production_order", order_id)
    db.commit()


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: DbSession, user: CurrentUser) -> DashboardOut:
    ensure_roles(user, UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT)
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
    ensure_roles(user, UserRole.ADMIN, UserRole.MANAGER)
    return await analyze_operations(db, data.question)


@router.post("/ai/shift-summary", response_model=AIAnalysisOut)
async def ai_shift_summary(data: AIShiftSummaryRequest, db: DbSession, user: CurrentUser) -> dict[str, object]:
    ensure_roles(user, UserRole.ADMIN, UserRole.MANAGER)
    shift = db.get(Shift, data.shift_id)
    if shift is None:
        raise HTTPException(404, "Không tìm thấy ca làm việc.")
    log_rows = list(
        db.scalars(
            select(ProductionLog)
            .where(ProductionLog.shift_id == shift.id)
            .order_by(ProductionLog.logged_at.desc())
            .limit(101)
        ).all()
    )
    logs = log_rows[:100]
    context = {
        "shift": {"name": shift.name, "start_time": shift.start_time.isoformat(), "end_time": shift.end_time.isoformat()},
        "logs_may_be_truncated": len(log_rows) > 100,
        "entries": [
            {
                "order_id": log.order_id,
                "good_quantity": log.good_quantity,
                "rejected_quantity": log.rejected_quantity,
                "incident_type": log.incident_type,
                "notes": log.notes,
                "logged_at": log.logged_at.isoformat(),
            }
            for log in logs
        ],
    }
    return await generate_ai_response(
        "Tóm tắt ca và các sự cố cần chú ý.",
        context,
        (PROJECT_ROOT / "backend" / "app" / "prompts" / "shift_summary_system.txt").read_text(encoding="utf-8"),
        f"Ca {shift.name}: {sum(log.good_quantity for log in logs)} sản phẩm đạt, "
        f"{sum(log.rejected_quantity for log in logs)} sản phẩm lỗi trên {len(logs)} nhật ký. "
        "Quản lý cần kiểm tra ghi chú sự cố.",
        f"{len(logs)} nhật ký của ca {shift.name}"
        + (" (giới hạn 100 bản ghi)" if len(log_rows) > 100 else ""),
    )


@router.post("/ai/customer-progress", response_model=AIAnalysisOut)
async def ai_customer_progress(
    data: AICustomerProgressRequest, db: DbSession, user: CurrentUser
) -> dict[str, object]:
    ensure_roles(user, UserRole.ADMIN, UserRole.MANAGER)
    order = db.get(ProductionOrder, data.order_id)
    if order is None:
        raise HTTPException(404, "Không tìm thấy đơn sản xuất.")
    context = {
        "order_code": order.order_code,
        "product_name": order.product_name,
        "quantity": order.quantity,
        "status": order.status.value,
        "due_date": order.due_date.isoformat() if order.due_date else None,
    }
    return await generate_ai_response(
        "Soạn bản nháp thông báo tiến độ cho khách hàng.",
        context,
        (PROJECT_ROOT / "backend" / "app" / "prompts" / "customer_progress_system.txt").read_text(encoding="utf-8"),
        f"Bản nháp: Đơn {order.order_code} ({order.product_name}) hiện "
        f"{order.status.value}; số lượng {order.quantity}. "
        f"{'Hạn dự kiến: ' + order.due_date.strftime('%d/%m/%Y') + '.' if order.due_date else 'Chưa có hạn hoàn thành.'} "
        "Vui lòng kiểm duyệt trước khi gửi.",
        f"Đơn hàng {order.order_code}",
    )


@router.post("/ai/technical-explanation", response_model=AIAnalysisOut)
async def ai_technical_explanation(
    data: AITechnicalExplanationRequest, db: DbSession, user: CurrentUser
) -> dict[str, object]:
    ensure_roles(user, UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)
    bom_rows = list(
        db.scalars(select(BOMItem).where(BOMItem.product_name.ilike(data.product_name.strip())).limit(201)).all()
    )
    operation_rows = list(
        db.scalars(
            select(ProductionOperation)
            .join(ProductionOrder)
            .where(ProductionOrder.product_name.ilike(data.product_name.strip()))
            .order_by(ProductionOperation.sequence)
            .limit(201)
        ).all()
    )
    bom = bom_rows[:200]
    operations = operation_rows[:200]
    context = {
        "product_name": data.product_name,
        "records_may_be_truncated": len(bom_rows) > 200 or len(operation_rows) > 200,
        "bom": [
            {
                "material": item.material.name,
                "unit": item.material.unit,
                "quantity_per_unit": float(item.quantity_per_unit),
                "instructions": item.notes,
            }
            for item in bom
        ],
        "operations": [
            {"stage": operation.stage_name, "sequence": operation.sequence, "instructions": operation.instructions}
            for operation in operations
        ],
    }
    prompt = (PROJECT_ROOT / "backend" / "app" / "prompts" / "technical_explanation_system.txt").read_text(
        encoding="utf-8"
    )
    fallback = (
        f"Chưa có BOM hoặc công đoạn được cấu hình cho {data.product_name}."
        if not bom and not operations
        else f"Sản phẩm {data.product_name}: {len(bom)} dòng định mức và {len(operations)} công đoạn đã cấu hình. "
        "Kiểm tra BOM và hướng dẫn công đoạn trong hệ thống; thông số an toàn phải theo quy trình chính thức."
    )
    return await generate_ai_response(
        "Giải thích BOM và trình tự công đoạn đã cấu hình.",
        context,
        prompt,
        fallback,
        f"{len(bom)} dòng BOM và {len(operations)} công đoạn cho {data.product_name}"
        + (" (giới hạn 200 bản ghi mỗi nhóm)" if context["records_may_be_truncated"] else ""),
    )


@router.get("/ai/status", response_model=AIStatusOut)
def ai_status(user: CurrentUser) -> AIStatusOut:
    del user
    if settings.gemini_api_key:
        return AIStatusOut(provider="gemini", model=settings.gemini_model)
    return AIStatusOut(provider="local", model="Phân tích quy tắc nội bộ")
