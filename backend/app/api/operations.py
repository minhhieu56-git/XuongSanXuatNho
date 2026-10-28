from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_UP

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, ensure_roles
from app.core.security import hash_password
from app.models import (
    AuditLog,
    BOMItem,
    Customer,
    Expense,
    InventoryItem,
    Invoice,
    MaterialIssue,
    Machine,
    Payment,
    ProductionLine,
    ProductionLog,
    ProductionOperation,
    ProductionOrder,
    QualityDefect,
    Shift,
    User,
    WorkSchedule,
    Worker,
)
from app.models.entities import (
    InvoiceStatus,
    MachineStatus,
    OperationStatus,
    OrderStatus,
    ScheduleStatus,
    UserRole,
    WorkerStatus,
)
from app.schemas.operations import (
    AdminUserCreate,
    AdminUserUpdate,
    AuditLogOut,
    BOMOut,
    BOMWrite,
    CustomerOut,
    CustomerWrite,
    DefectOut,
    DefectWrite,
    ExpenseOut,
    ExpenseWrite,
    FinancialReportOut,
    InvoiceOut,
    InvoiceWrite,
    MaterialIssueOut,
    MachineOut,
    MachineWrite,
    OperationOut,
    OperationWrite,
    OrderProgressOut,
    MaterialRequirementOut,
    PaymentOut,
    PaymentWrite,
    ProductionLineOut,
    ProductionLineWrite,
    ProductionLogOut,
    ProductionLogWrite,
    ScheduleOut,
    ScheduleWrite,
    ShiftOut,
    ShiftWrite,
    WorkerOut,
    WorkerWrite,
)
from app.schemas.api import UserOut

router = APIRouter()
MANAGERS = (UserRole.ADMIN, UserRole.MANAGER)
PRODUCTION_STAFF = (*MANAGERS, UserRole.WORKER)
MATERIAL_QUANTUM = Decimal("0.01")


def _round_material_quantity(value: Decimal) -> Decimal:
    return value.quantize(MATERIAL_QUANTUM, rounding=ROUND_UP)


def _check_worker_order_access(db: Session, user: User, order_id: int) -> None:
    if user.role != UserRole.WORKER:
        return
    worker = db.scalar(select(Worker).where(Worker.user_id == user.id))
    if worker is None or db.scalar(
        select(WorkSchedule.id)
        .where(WorkSchedule.order_id == order_id, WorkSchedule.worker_id == worker.id)
        .limit(1)
    ) is None:
        raise HTTPException(403, "Bạn chỉ được xem đơn hàng được phân công.")


def _commit(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, message) from exc


def _audit(db: Session, user: User, action: str, entity: str, entity_id: int | None = None) -> None:
    db.add(AuditLog(user_id=user.id, action=action, entity_type=entity, entity_id=entity_id))


@router.get("/admin/users", response_model=list[UserOut])
def list_users(db: DbSession, user: CurrentUser) -> list[User]:
    ensure_roles(user, UserRole.ADMIN)
    return list(db.scalars(select(User).order_by(User.id).limit(500)).all())


@router.get("/admin/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(
    db: DbSession,
    user: CurrentUser,
    entity_type: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditLog]:
    ensure_roles(user, UserRole.ADMIN)
    query = select(AuditLog)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    return list(db.scalars(query.order_by(AuditLog.created_at.desc()).limit(limit)).all())


@router.post("/admin/users", response_model=UserOut, status_code=201)
def create_user(data: AdminUserCreate, db: DbSession, user: CurrentUser) -> User:
    ensure_roles(user, UserRole.ADMIN)
    email = data.email.strip().lower()
    account = User(
        email=email,
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(account)
    try:
        db.flush()
        _audit(db, user, "create", "user", account.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Email tài khoản đã được sử dụng.") from exc
    db.refresh(account)
    return account


@router.put("/admin/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: AdminUserUpdate, db: DbSession, user: CurrentUser) -> User:
    ensure_roles(user, UserRole.ADMIN)
    account = db.get(User, user_id)
    if account is None:
        raise HTTPException(404, "Không tìm thấy tài khoản.")
    if account.id == user.id and (not data.is_active or data.role != UserRole.ADMIN):
        raise HTTPException(422, "Không thể tự vô hiệu hóa hoặc hạ quyền tài khoản đang đăng nhập.")
    account.role = data.role
    account.is_active = data.is_active
    if data.password:
        account.password_hash = hash_password(data.password)
    _audit(db, user, "update", "user", account.id)
    _commit(db, "Không thể cập nhật tài khoản.")
    db.refresh(account)
    return account


@router.delete("/admin/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: DbSession, user: CurrentUser) -> None:
    ensure_roles(user, UserRole.ADMIN)
    account = db.get(User, user_id)
    if account is None:
        raise HTTPException(404, "Không tìm thấy tài khoản.")
    if account.id == user.id:
        raise HTTPException(422, "Không thể xóa tài khoản đang đăng nhập; hãy nhờ quản trị viên khác.")
    db.delete(account)
    _audit(db, user, "delete", "user", user_id)
    _commit(db, "Tài khoản đang được dữ liệu nghiệp vụ sử dụng; hãy vô hiệu hóa thay vì xóa.")


def _validate_refs(db: Session, **refs: tuple[type, int | None]) -> None:
    for label, (model, identifier) in refs.items():
        if identifier is not None and db.get(model, identifier) is None:
            raise HTTPException(422, f"{label} được chọn không tồn tại.")


def _check_schedule_conflict(
    db: Session, data: ScheduleWrite, exclude_id: int | None = None
) -> None:
    if data.status in (ScheduleStatus.CANCELLED, ScheduleStatus.COMPLETED):
        return
    if db.bind and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(827341)"))
    query = select(WorkSchedule).where(
        WorkSchedule.status.in_((ScheduleStatus.SCHEDULED, ScheduleStatus.IN_PROGRESS)),
        WorkSchedule.starts_at < data.ends_at,
        WorkSchedule.ends_at > data.starts_at,
        or_(WorkSchedule.worker_id == data.worker_id, WorkSchedule.machine_id == data.machine_id),
    )
    if exclude_id is not None:
        query = query.where(WorkSchedule.id != exclude_id)
    if db.scalar(query.limit(1)) is not None:
        raise HTTPException(409, "Công nhân hoặc máy đã có lịch trùng trong khoảng thời gian này.")


@router.get("/workers", response_model=list[WorkerOut])
def list_workers(
    db: DbSession,
    user: CurrentUser,
    search: str = Query(default="", max_length=120),
    worker_status: WorkerStatus | None = None,
) -> list[Worker]:
    ensure_roles(user, *PRODUCTION_STAFF)
    query = select(Worker)
    if user.role == UserRole.WORKER:
        query = query.where(Worker.user_id == user.id)
    if search.strip():
        term = f"%{search.strip()}%"
        query = query.where(or_(Worker.worker_code.ilike(term), Worker.full_name.ilike(term)))
    if worker_status:
        query = query.where(Worker.status == worker_status)
    return list(db.scalars(query.order_by(Worker.full_name)).all())


@router.post("/workers", response_model=WorkerOut, status_code=201)
def create_worker(data: WorkerWrite, db: DbSession, user: CurrentUser) -> Worker:
    ensure_roles(user, *MANAGERS)
    _validate_refs(db, **{"Tài khoản": (User, data.user_id)})
    if data.user_id is not None and db.get(User, data.user_id).role != UserRole.WORKER:
        raise HTTPException(422, "Tài khoản liên kết phải có vai trò công nhân.")
    worker = Worker(**data.model_dump())
    db.add(worker)
    db.flush()
    _audit(db, user, "create", "worker", worker.id)
    _commit(db, "Mã công nhân hoặc tài khoản liên kết đã được sử dụng.")
    db.refresh(worker)
    return worker


@router.put("/workers/{worker_id}", response_model=WorkerOut)
def update_worker(worker_id: int, data: WorkerWrite, db: DbSession, user: CurrentUser) -> Worker:
    ensure_roles(user, *MANAGERS)
    worker = db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(404, "Không tìm thấy công nhân.")
    _validate_refs(db, **{"Tài khoản": (User, data.user_id)})
    for key, value in data.model_dump().items():
        setattr(worker, key, value)
    _audit(db, user, "update", "worker", worker.id)
    _commit(db, "Mã công nhân hoặc tài khoản liên kết đã được sử dụng.")
    db.refresh(worker)
    return worker


@router.delete("/workers/{worker_id}", status_code=204)
def delete_worker(worker_id: int, db: DbSession, user: CurrentUser) -> None:
    ensure_roles(user, *MANAGERS)
    worker = db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(404, "Không tìm thấy công nhân.")
    db.delete(worker)
    _audit(db, user, "delete", "worker", worker_id)
    _commit(db, "Không thể xóa công nhân đang được sử dụng trong lịch hoặc nhật ký.")


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(db: DbSession, user: CurrentUser, search: str = Query(default="", max_length=120)):
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT)
    query = select(Customer)
    if search.strip():
        term = f"%{search.strip()}%"
        query = query.where(or_(Customer.customer_code.ilike(term), Customer.full_name.ilike(term)))
    return list(db.scalars(query.order_by(Customer.full_name)).all())


@router.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(data: CustomerWrite, db: DbSession, user: CurrentUser) -> Customer:
    ensure_roles(user, *MANAGERS)
    _validate_refs(db, **{"Tài khoản": (User, data.user_id)})
    if data.user_id is not None and db.get(User, data.user_id).role != UserRole.CUSTOMER:
        raise HTTPException(422, "Tài khoản liên kết phải có vai trò khách hàng.")
    customer = Customer(**data.model_dump())
    db.add(customer)
    db.flush()
    _audit(db, user, "create", "customer", customer.id)
    _commit(db, "Mã khách hàng hoặc tài khoản liên kết đã được sử dụng.")
    db.refresh(customer)
    return customer


@router.put("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, data: CustomerWrite, db: DbSession, user: CurrentUser) -> Customer:
    ensure_roles(user, *MANAGERS)
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(404, "Không tìm thấy khách hàng.")
    _validate_refs(db, **{"Tài khoản": (User, data.user_id)})
    for key, value in data.model_dump().items():
        setattr(customer, key, value)
    _audit(db, user, "update", "customer", customer.id)
    _commit(db, "Mã khách hàng hoặc tài khoản liên kết đã được sử dụng.")
    db.refresh(customer)
    return customer


@router.delete("/customers/{customer_id}", status_code=204)
def delete_customer(customer_id: int, db: DbSession, user: CurrentUser) -> None:
    ensure_roles(user, *MANAGERS)
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(404, "Không tìm thấy khách hàng.")
    db.delete(customer)
    _audit(db, user, "delete", "customer", customer_id)
    _commit(db, "Không thể xóa khách hàng đã liên kết với đơn hàng.")


@router.get("/production-lines", response_model=list[ProductionLineOut])
def list_lines(db: DbSession, user: CurrentUser):
    ensure_roles(user, *PRODUCTION_STAFF)
    return list(db.scalars(select(ProductionLine).order_by(ProductionLine.name)).all())


@router.post("/production-lines", response_model=ProductionLineOut, status_code=201)
def create_line(data: ProductionLineWrite, db: DbSession, user: CurrentUser) -> ProductionLine:
    ensure_roles(user, *MANAGERS)
    line = ProductionLine(**data.model_dump())
    db.add(line)
    db.flush()
    _audit(db, user, "create", "production_line", line.id)
    _commit(db, "Mã dây chuyền đã tồn tại.")
    db.refresh(line)
    return line


@router.put("/production-lines/{line_id}", response_model=ProductionLineOut)
def update_line(line_id: int, data: ProductionLineWrite, db: DbSession, user: CurrentUser) -> ProductionLine:
    ensure_roles(user, *MANAGERS)
    line = db.get(ProductionLine, line_id)
    if line is None:
        raise HTTPException(404, "Không tìm thấy dây chuyền.")
    for key, value in data.model_dump().items():
        setattr(line, key, value)
    _audit(db, user, "update", "production_line", line.id)
    _commit(db, "Mã dây chuyền đã tồn tại.")
    db.refresh(line)
    return line


@router.delete("/production-lines/{line_id}", status_code=204)
def delete_line(line_id: int, db: DbSession, user: CurrentUser) -> None:
    ensure_roles(user, *MANAGERS)
    line = db.get(ProductionLine, line_id)
    if line is None:
        raise HTTPException(404, "Không tìm thấy dây chuyền.")
    db.delete(line)
    _audit(db, user, "delete", "production_line", line_id)
    _commit(db, "Không thể xóa dây chuyền đang được máy hoặc lịch sử dụng.")


@router.get("/machines", response_model=list[MachineOut])
def list_machines(db: DbSession, user: CurrentUser, machine_status: MachineStatus | None = None):
    ensure_roles(user, *PRODUCTION_STAFF)
    query = select(Machine)
    if machine_status:
        query = query.where(Machine.status == machine_status)
    return list(db.scalars(query.order_by(Machine.machine_code)).all())


@router.post("/machines", response_model=MachineOut, status_code=201)
def create_machine(data: MachineWrite, db: DbSession, user: CurrentUser) -> Machine:
    ensure_roles(user, *MANAGERS)
    _validate_refs(db, **{"Dây chuyền": (ProductionLine, data.line_id)})
    machine = Machine(**data.model_dump())
    db.add(machine)
    db.flush()
    _audit(db, user, "create", "machine", machine.id)
    _commit(db, "Mã máy đã tồn tại.")
    db.refresh(machine)
    return machine


@router.put("/machines/{machine_id}", response_model=MachineOut)
def update_machine(machine_id: int, data: MachineWrite, db: DbSession, user: CurrentUser) -> Machine:
    ensure_roles(user, *MANAGERS)
    machine = db.get(Machine, machine_id)
    if machine is None:
        raise HTTPException(404, "Không tìm thấy máy.")
    _validate_refs(db, **{"Dây chuyền": (ProductionLine, data.line_id)})
    for key, value in data.model_dump().items():
        setattr(machine, key, value)
    _audit(db, user, "update", "machine", machine.id)
    _commit(db, "Mã máy đã tồn tại.")
    db.refresh(machine)
    return machine


@router.delete("/machines/{machine_id}", status_code=204)
def delete_machine(machine_id: int, db: DbSession, user: CurrentUser) -> None:
    ensure_roles(user, *MANAGERS)
    machine = db.get(Machine, machine_id)
    if machine is None:
        raise HTTPException(404, "Không tìm thấy máy.")
    db.delete(machine)
    _audit(db, user, "delete", "machine", machine_id)
    _commit(db, "Không thể xóa máy đang được lịch hoặc nhật ký sử dụng.")


@router.get("/shifts", response_model=list[ShiftOut])
def list_shifts(db: DbSession, user: CurrentUser):
    ensure_roles(user, *PRODUCTION_STAFF)
    return list(db.scalars(select(Shift).order_by(Shift.start_time)).all())


@router.post("/shifts", response_model=ShiftOut, status_code=201)
def create_shift(data: ShiftWrite, db: DbSession, user: CurrentUser) -> Shift:
    ensure_roles(user, *MANAGERS)
    shift = Shift(**data.model_dump())
    db.add(shift)
    db.flush()
    _audit(db, user, "create", "shift", shift.id)
    _commit(db, "Tên ca làm việc đã tồn tại.")
    db.refresh(shift)
    return shift


@router.put("/shifts/{shift_id}", response_model=ShiftOut)
def update_shift(shift_id: int, data: ShiftWrite, db: DbSession, user: CurrentUser) -> Shift:
    ensure_roles(user, *MANAGERS)
    shift = db.get(Shift, shift_id)
    if shift is None:
        raise HTTPException(404, "Không tìm thấy ca làm việc.")
    for key, value in data.model_dump().items():
        setattr(shift, key, value)
    _audit(db, user, "update", "shift", shift.id)
    _commit(db, "Tên ca làm việc đã tồn tại.")
    db.refresh(shift)
    return shift


@router.delete("/shifts/{shift_id}", status_code=204)
def delete_shift(shift_id: int, db: DbSession, user: CurrentUser) -> None:
    ensure_roles(user, *MANAGERS)
    shift = db.get(Shift, shift_id)
    if shift is None:
        raise HTTPException(404, "Không tìm thấy ca làm việc.")
    db.delete(shift)
    _audit(db, user, "delete", "shift", shift_id)
    _commit(db, "Không thể xóa ca đang được lịch hoặc nhật ký sử dụng.")


@router.get("/schedules", response_model=list[ScheduleOut])
def list_schedules(db: DbSession, user: CurrentUser):
    ensure_roles(user, *PRODUCTION_STAFF)
    query = select(WorkSchedule)
    if user.role == UserRole.WORKER:
        worker = db.scalar(select(Worker).where(Worker.user_id == user.id))
        query = query.where(WorkSchedule.worker_id == (worker.id if worker else -1))
    return list(db.scalars(query.order_by(WorkSchedule.starts_at)).all())


@router.post("/schedules", response_model=ScheduleOut, status_code=201)
def create_schedule(data: ScheduleWrite, db: DbSession, user: CurrentUser) -> WorkSchedule:
    ensure_roles(user, *MANAGERS)
    _validate_refs(db, **{
        "Đơn hàng": (ProductionOrder, data.order_id),
        "Công nhân": (Worker, data.worker_id),
        "Máy": (Machine, data.machine_id),
        "Dây chuyền": (ProductionLine, data.line_id),
        "Ca": (Shift, data.shift_id),
    })
    if db.get(ProductionOrder, data.order_id).status == OrderStatus.CANCELLED:
        raise HTTPException(422, "Không thể xếp lịch cho đơn đã hủy.")
    _check_schedule_conflict(db, data)
    schedule = WorkSchedule(**data.model_dump(), created_by_id=user.id)
    db.add(schedule)
    db.flush()
    _audit(db, user, "create", "schedule", schedule.id)
    _commit(db, "Lịch bị trùng hoặc tham chiếu không hợp lệ.")
    db.refresh(schedule)
    return schedule


@router.put("/schedules/{schedule_id}", response_model=ScheduleOut)
def update_schedule(schedule_id: int, data: ScheduleWrite, db: DbSession, user: CurrentUser) -> WorkSchedule:
    ensure_roles(user, *MANAGERS)
    schedule = db.get(WorkSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(404, "Không tìm thấy lịch làm việc.")
    _validate_refs(db, **{
        "Đơn hàng": (ProductionOrder, data.order_id),
        "Công nhân": (Worker, data.worker_id),
        "Máy": (Machine, data.machine_id),
        "Dây chuyền": (ProductionLine, data.line_id),
        "Ca": (Shift, data.shift_id),
    })
    _check_schedule_conflict(db, data, schedule.id)
    for key, value in data.model_dump().items():
        setattr(schedule, key, value)
    _audit(db, user, "update", "schedule", schedule.id)
    _commit(db, "Lịch bị trùng hoặc tham chiếu không hợp lệ.")
    db.refresh(schedule)
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: int, db: DbSession, user: CurrentUser) -> None:
    ensure_roles(user, *MANAGERS)
    schedule = db.get(WorkSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(404, "Không tìm thấy lịch làm việc.")
    db.delete(schedule)
    _audit(db, user, "delete", "schedule", schedule_id)
    _commit(db, "Không thể xóa lịch làm việc.")


@router.get("/bom", response_model=list[BOMOut])
def list_bom(db: DbSession, user: CurrentUser, product_name: str | None = Query(default=None, max_length=160)):
    ensure_roles(user, *PRODUCTION_STAFF)
    query = select(BOMItem)
    if product_name:
        query = query.where(BOMItem.product_name.ilike(f"%{product_name.strip()}%"))
    return list(db.scalars(query.order_by(BOMItem.product_name, BOMItem.id)).all())


@router.post("/bom", response_model=BOMOut, status_code=201)
def create_bom(data: BOMWrite, db: DbSession, user: CurrentUser) -> BOMItem:
    ensure_roles(user, *MANAGERS)
    _ensure_bom_not_issued(db, data.product_name)
    _validate_refs(db, **{"Nguyên liệu": (InventoryItem, data.material_id)})
    item = BOMItem(**data.model_dump())
    db.add(item)
    db.flush()
    _audit(db, user, "create", "bom_item", item.id)
    _commit(db, "Định mức vật tư cho sản phẩm và nguyên liệu này đã tồn tại.")
    db.refresh(item)
    return item


@router.put("/bom/{item_id}", response_model=BOMOut)
def update_bom(item_id: int, data: BOMWrite, db: DbSession, user: CurrentUser) -> BOMItem:
    ensure_roles(user, *MANAGERS)
    item = db.get(BOMItem, item_id)
    if item is None:
        raise HTTPException(404, "Không tìm thấy dòng định mức.")
    _ensure_bom_not_issued(db, item.product_name)
    if data.product_name != item.product_name:
        _ensure_bom_not_issued(db, data.product_name)
    _validate_refs(db, **{"Nguyên liệu": (InventoryItem, data.material_id)})
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    _audit(db, user, "update", "bom_item", item.id)
    _commit(db, "Định mức vật tư cho sản phẩm và nguyên liệu này đã tồn tại.")
    db.refresh(item)
    return item


@router.delete("/bom/{item_id}", status_code=204)
def delete_bom(item_id: int, db: DbSession, user: CurrentUser) -> None:
    ensure_roles(user, *MANAGERS)
    item = db.get(BOMItem, item_id)
    if item is None:
        raise HTTPException(404, "Không tìm thấy dòng định mức.")
    _ensure_bom_not_issued(db, item.product_name)
    db.delete(item)
    _audit(db, user, "delete", "bom_item", item_id)
    _commit(db, "Không thể xóa dòng định mức.")


@router.get("/orders/{order_id}/progress", response_model=OrderProgressOut)
def get_order_progress(order_id: int, db: DbSession, user: CurrentUser) -> OrderProgressOut:
    ensure_roles(user, *PRODUCTION_STAFF, UserRole.CUSTOMER)
    order = db.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(404, "Không tìm thấy đơn sản xuất.")
    if user.role == UserRole.CUSTOMER:
        customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
        if customer is None or order.customer_id != customer.id:
            raise HTTPException(404, "Không tìm thấy đơn sản xuất.")
    else:
        _check_worker_order_access(db, user, order_id)

    operations = list(
        db.scalars(
            select(ProductionOperation)
            .where(ProductionOperation.order_id == order_id)
            .order_by(ProductionOperation.sequence)
        ).all()
    )
    return _build_order_progress(order, operations)


def _build_order_progress(
    order: ProductionOrder, operations: list[ProductionOperation]
) -> OrderProgressOut:
    completed = sum(operation.completed_quantity for operation in operations)
    rejected = sum(operation.rejected_quantity for operation in operations)
    if not operations:
        progress = Decimal(100 if order.status == OrderStatus.COMPLETED else 0)
    else:
        stage_progress = [
            min(Decimal(operation.completed_quantity + operation.rejected_quantity) / order.quantity, Decimal(1))
            for operation in operations
        ]
        progress = (sum(stage_progress, Decimal(0)) / len(stage_progress) * 100).quantize(
            Decimal("0.01")
        )
    return OrderProgressOut(
        order_id=order.id,
        order_code=order.order_code,
        status=order.status.value,
        target_quantity=order.quantity,
        completed_quantity=completed,
        rejected_quantity=rejected,
        progress_percent=float(progress),
        operations=operations,
    )


@router.get("/orders/progress", response_model=list[OrderProgressOut])
def list_order_progress(db: DbSession, user: CurrentUser) -> list[OrderProgressOut]:
    ensure_roles(user, *PRODUCTION_STAFF, UserRole.CUSTOMER)
    query = select(ProductionOrder)
    if user.role == UserRole.CUSTOMER:
        customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
        query = query.where(ProductionOrder.customer_id == (customer.id if customer else -1))
    elif user.role == UserRole.WORKER:
        worker = db.scalar(select(Worker).where(Worker.user_id == user.id))
        query = query.join(WorkSchedule).where(
            WorkSchedule.worker_id == (worker.id if worker else -1)
        ).distinct()
    orders = list(db.scalars(query.order_by(ProductionOrder.id)).all())
    if not orders:
        return []
    operations = list(
        db.scalars(
            select(ProductionOperation)
            .where(ProductionOperation.order_id.in_([order.id for order in orders]))
            .order_by(ProductionOperation.order_id, ProductionOperation.sequence)
        ).all()
    )
    operations_by_order: dict[int, list[ProductionOperation]] = {}
    for operation in operations:
        operations_by_order.setdefault(operation.order_id, []).append(operation)
    return [
        _build_order_progress(order, operations_by_order.get(order.id, []))
        for order in orders
    ]


def _material_requirements(db: Session, order: ProductionOrder) -> list[dict]:
    bom_items = list(
        db.scalars(
            select(BOMItem)
            .where(BOMItem.product_name == order.product_name)
            .order_by(BOMItem.material_id)
        ).all()
    )
    if not bom_items:
        raise HTTPException(409, "Sản phẩm chưa có định mức BOM.")

    issue_totals = dict(
        db.execute(
            select(MaterialIssue.material_id, func.coalesce(func.sum(MaterialIssue.quantity), 0))
            .where(MaterialIssue.order_id == order.id)
            .group_by(MaterialIssue.material_id)
        ).all()
    )
    requirements: list[dict] = []
    for bom_item in bom_items:
        material = db.get(InventoryItem, bom_item.material_id)
        required = _round_material_quantity(Decimal(order.quantity) * bom_item.quantity_per_unit)
        issued = Decimal(issue_totals.get(material.id, 0))
        requirements.append({
            "material_id": material.id,
            "sku": material.sku,
            "material_name": material.name,
            "unit": material.unit,
            "required_quantity": required,
            "issued_quantity": issued,
            "remaining_quantity": max(required - issued, Decimal(0)),
            "available_quantity": material.quantity,
        })
    return requirements


def _ensure_bom_not_issued(db: Session, product_name: str) -> None:
    has_issues = db.scalar(
        select(MaterialIssue.id)
        .join(ProductionOrder, ProductionOrder.id == MaterialIssue.order_id)
        .where(ProductionOrder.product_name == product_name)
        .limit(1)
    )
    if has_issues is not None:
        raise HTTPException(409, "Không thể thay đổi BOM sau khi đã xuất vật tư cho sản phẩm.")


@router.get("/orders/{order_id}/material-requirements", response_model=list[MaterialRequirementOut])
def get_material_requirements(order_id: int, db: DbSession, user: CurrentUser):
    ensure_roles(user, *PRODUCTION_STAFF)
    order = db.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(404, "Không tìm thấy đơn sản xuất.")
    _check_worker_order_access(db, user, order_id)
    return _material_requirements(db, order)


@router.get("/material-issues", response_model=list[MaterialIssueOut])
def list_material_issues(
    db: DbSession,
    user: CurrentUser,
    order_id: int | None = None,
):
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT)
    query = select(MaterialIssue)
    if order_id is not None:
        query = query.where(MaterialIssue.order_id == order_id)
    return list(db.scalars(query.order_by(MaterialIssue.issued_at.desc()).limit(500)).all())


@router.post("/orders/{order_id}/materials/issue", response_model=list[MaterialIssueOut], status_code=201)
def issue_order_materials(order_id: int, db: DbSession, user: CurrentUser):
    ensure_roles(user, *MANAGERS)
    order = db.scalar(
        select(ProductionOrder).where(ProductionOrder.id == order_id).with_for_update()
    )
    if order is None:
        raise HTTPException(404, "Không tìm thấy đơn sản xuất.")
    if order.status in (OrderStatus.CANCELLED, OrderStatus.COMPLETED):
        raise HTTPException(409, "Không thể xuất vật tư cho đơn đã hủy hoặc hoàn thành.")

    requirements = _material_requirements(db, order)
    remaining_requirements = [
        requirement for requirement in requirements if requirement["remaining_quantity"] > 0
    ]
    if not remaining_requirements:
        raise HTTPException(409, "Định mức vật tư của đơn hàng đã được xuất đủ.")

    material_ids = [item["material_id"] for item in remaining_requirements]
    materials = {
        material.id: material
        for material in db.scalars(
            select(InventoryItem)
            .where(InventoryItem.id.in_(material_ids))
            .order_by(InventoryItem.id)
            .with_for_update()
        ).all()
    }
    insufficient = [
        f"{item['sku']}: cần {item['remaining_quantity']} {item['unit']}, "
        f"tồn {materials[item['material_id']].quantity} {item['unit']}"
        for item in remaining_requirements
        if materials[item["material_id"]].quantity < item["remaining_quantity"]
    ]
    if insufficient:
        raise HTTPException(409, "Tồn kho không đủ; chưa xuất vật tư. " + "; ".join(insufficient))

    issues: list[MaterialIssue] = []
    for requirement in remaining_requirements:
        material = materials[requirement["material_id"]]
        quantity = requirement["remaining_quantity"]
        material.quantity -= quantity
        issue = MaterialIssue(
            order_id=order.id,
            material_id=material.id,
            quantity=quantity,
            issued_by_id=user.id,
        )
        db.add(issue)
        issues.append(issue)
    db.flush()
    _audit(db, user, "issue", "order_materials", order.id)
    _commit(db, "Không thể xuất vật tư; tồn kho hoặc định mức đã thay đổi.")
    for issue in issues:
        db.refresh(issue)
    return issues


@router.get("/operations", response_model=list[OperationOut])
def list_operations(db: DbSession, user: CurrentUser, order_id: int | None = None):
    ensure_roles(user, *PRODUCTION_STAFF)
    query = select(ProductionOperation)
    if order_id is not None:
        query = query.where(ProductionOperation.order_id == order_id)
    if user.role == UserRole.WORKER:
        worker = db.scalar(select(Worker).where(Worker.user_id == user.id))
        query = query.join(
            WorkSchedule, WorkSchedule.order_id == ProductionOperation.order_id
        ).where(WorkSchedule.worker_id == (worker.id if worker else -1)).distinct()
    return list(db.scalars(query.order_by(ProductionOperation.order_id, ProductionOperation.sequence)).all())


@router.post("/operations", response_model=OperationOut, status_code=201)
def create_operation(data: OperationWrite, db: DbSession, user: CurrentUser) -> ProductionOperation:
    ensure_roles(user, *MANAGERS)
    _validate_refs(db, **{"Đơn hàng": (ProductionOrder, data.order_id)})
    if data.completed_quantity + data.rejected_quantity > db.get(
        ProductionOrder, data.order_id
    ).quantity:
        raise HTTPException(422, "Sản lượng công đoạn không được vượt số lượng đơn hàng.")
    operation = ProductionOperation(**data.model_dump())
    db.add(operation)
    db.flush()
    _audit(db, user, "create", "production_operation", operation.id)
    _commit(db, "Thứ tự công đoạn trong đơn hàng đã tồn tại.")
    db.refresh(operation)
    return operation


@router.put("/operations/{operation_id}", response_model=OperationOut)
def update_operation(operation_id: int, data: OperationWrite, db: DbSession, user: CurrentUser):
    ensure_roles(user, *MANAGERS)
    operation = db.get(ProductionOperation, operation_id)
    if operation is None:
        raise HTTPException(404, "Không tìm thấy công đoạn.")
    _validate_refs(db, **{"Đơn hàng": (ProductionOrder, data.order_id)})
    order = db.get(ProductionOrder, data.order_id)
    if data.completed_quantity + data.rejected_quantity > order.quantity:
        raise HTTPException(422, "Sản lượng công đoạn không được vượt số lượng đơn hàng.")
    for key, value in data.model_dump().items():
        setattr(operation, key, value)
    _audit(db, user, "update", "production_operation", operation.id)
    _commit(db, "Thứ tự công đoạn trong đơn hàng đã tồn tại.")
    db.refresh(operation)
    return operation


@router.delete("/operations/{operation_id}", status_code=204)
def delete_operation(operation_id: int, db: DbSession, user: CurrentUser) -> None:
    ensure_roles(user, *MANAGERS)
    operation = db.get(ProductionOperation, operation_id)
    if operation is None:
        raise HTTPException(404, "Không tìm thấy công đoạn.")
    if operation.status != OperationStatus.PLANNED or db.scalar(
        select(ProductionLog.id).where(ProductionLog.operation_id == operation.id).limit(1)
    ):
        raise HTTPException(409, "Chỉ công đoạn chưa thực hiện và chưa có nhật ký mới được xóa.")
    db.delete(operation)
    _audit(db, user, "delete", "production_operation", operation_id)
    _commit(db, "Không thể xóa công đoạn.")


@router.post("/production-logs", response_model=ProductionLogOut, status_code=201)
def create_production_log(data: ProductionLogWrite, db: DbSession, user: CurrentUser) -> ProductionLog:
    ensure_roles(user, *PRODUCTION_STAFF)
    _validate_refs(db, **{
        "Đơn hàng": (ProductionOrder, data.order_id),
        "Công đoạn": (ProductionOperation, data.operation_id),
        "Công nhân": (Worker, data.worker_id),
        "Máy": (Machine, data.machine_id),
        "Ca": (Shift, data.shift_id),
    })
    if user.role == UserRole.WORKER:
        worker = db.scalar(select(Worker).where(Worker.user_id == user.id))
        if worker is None or data.worker_id not in (None, worker.id):
            raise HTTPException(403, "Bạn chỉ được ghi nhật ký sản xuất của chính mình.")
        data.worker_id = worker.id
    log = ProductionLog(**data.model_dump(), logged_by_id=user.id)
    db.add(log)
    if data.operation_id is not None:
        operation = db.get(ProductionOperation, data.operation_id)
        if operation.order_id != data.order_id:
            raise HTTPException(422, "Công đoạn không thuộc đơn hàng đã chọn.")
        if user.role == UserRole.WORKER:
            _check_worker_order_access(db, user, data.order_id)
        if operation.completed_quantity + operation.rejected_quantity + data.good_quantity + data.rejected_quantity > db.get(
            ProductionOrder, data.order_id
        ).quantity:
            raise HTTPException(422, "Sản lượng nhật ký vượt số lượng đơn hàng.")
        operation.completed_quantity += data.good_quantity
        operation.rejected_quantity += data.rejected_quantity
        if operation.completed_quantity + operation.rejected_quantity >= db.get(
            ProductionOrder, data.order_id
        ).quantity:
            operation.status = OperationStatus.COMPLETED
        elif operation.completed_quantity + operation.rejected_quantity > 0:
            operation.status = OperationStatus.IN_PROGRESS
    elif user.role == UserRole.WORKER:
        _check_worker_order_access(db, user, data.order_id)
    db.flush()
    _audit(db, user, "create", "production_log", log.id)
    _commit(db, "Không thể lưu nhật ký sản xuất.")
    db.refresh(log)
    return log


@router.get("/production-logs", response_model=list[ProductionLogOut])
def list_production_logs(db: DbSession, user: CurrentUser, order_id: int | None = None):
    ensure_roles(user, *PRODUCTION_STAFF)
    query = select(ProductionLog)
    if user.role == UserRole.WORKER:
        query = query.where(ProductionLog.logged_by_id == user.id)
    if order_id is not None:
        query = query.where(ProductionLog.order_id == order_id)
    return list(db.scalars(query.order_by(ProductionLog.logged_at.desc()).limit(500)).all())


@router.get("/defects", response_model=list[DefectOut])
def list_defects(db: DbSession, user: CurrentUser, order_id: int | None = None):
    ensure_roles(user, *MANAGERS)
    query = select(QualityDefect)
    if order_id is not None:
        query = query.where(QualityDefect.order_id == order_id)
    return list(db.scalars(query.order_by(QualityDefect.reported_at.desc()).limit(500)).all())


@router.post("/defects", response_model=DefectOut, status_code=201)
def create_defect(data: DefectWrite, db: DbSession, user: CurrentUser) -> QualityDefect:
    ensure_roles(user, *PRODUCTION_STAFF)
    _check_worker_order_access(db, user, data.order_id)
    _validate_refs(db, **{
        "Đơn hàng": (ProductionOrder, data.order_id),
        "Công đoạn": (ProductionOperation, data.operation_id),
    })
    if data.operation_id and db.get(ProductionOperation, data.operation_id).order_id != data.order_id:
        raise HTTPException(422, "Công đoạn không thuộc đơn hàng đã chọn.")
    defect = QualityDefect(**data.model_dump(), reported_by_id=user.id)
    db.add(defect)
    db.flush()
    _audit(db, user, "create", "quality_defect", defect.id)
    _commit(db, "Không thể lưu lỗi chất lượng.")
    db.refresh(defect)
    return defect


@router.put("/defects/{defect_id}", response_model=DefectOut)
def update_defect(defect_id: int, data: DefectWrite, db: DbSession, user: CurrentUser) -> QualityDefect:
    ensure_roles(user, *MANAGERS)
    defect = db.get(QualityDefect, defect_id)
    if defect is None:
        raise HTTPException(404, "Không tìm thấy lỗi chất lượng.")
    _validate_refs(db, **{
        "Đơn hàng": (ProductionOrder, data.order_id),
        "Công đoạn": (ProductionOperation, data.operation_id),
    })
    if data.operation_id and db.get(ProductionOperation, data.operation_id).order_id != data.order_id:
        raise HTTPException(422, "Công đoạn không thuộc đơn hàng đã chọn.")
    for key, value in data.model_dump().items():
        setattr(defect, key, value)
    _audit(db, user, "update", "quality_defect", defect.id)
    _commit(db, "Không thể cập nhật lỗi chất lượng.")
    db.refresh(defect)
    return defect


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(db: DbSession, user: CurrentUser):
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT, UserRole.CUSTOMER)
    query = select(Invoice)
    if user.role == UserRole.CUSTOMER:
        customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
        query = query.join(ProductionOrder).where(
            ProductionOrder.customer_id == (customer.id if customer else -1)
        )
    return list(db.scalars(query.order_by(Invoice.id.desc())).all())


@router.post("/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice(data: InvoiceWrite, db: DbSession, user: CurrentUser) -> Invoice:
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT)
    if data.status not in (InvoiceStatus.DRAFT, InvoiceStatus.ISSUED):
        raise HTTPException(422, "Hóa đơn mới chỉ được tạo ở trạng thái nháp hoặc đã phát hành.")
    order = db.get(ProductionOrder, data.order_id)
    if order is None:
        raise HTTPException(422, "Đơn hàng không tồn tại.")
    if db.scalar(select(Invoice.id).where(Invoice.order_id == data.order_id).limit(1)) is not None:
        raise HTTPException(409, "Đơn hàng này đã có hóa đơn. Hãy chọn một đơn chưa lập hóa đơn.")
    subtotal = Decimal(order.quantity) * data.service_unit_price
    if data.discount_amount > subtotal:
        raise HTTPException(422, "Chiết khấu không được lớn hơn thành tiền.")
    invoice = Invoice(
        **data.model_dump(),
        subtotal=subtotal,
        total_amount=subtotal - data.discount_amount,
        amount_paid=Decimal(0),
        issued_at=datetime.now(timezone.utc) if data.status != InvoiceStatus.DRAFT else None,
        created_by_id=user.id,
    )
    db.add(invoice)
    db.flush()
    _audit(db, user, "create", "invoice", invoice.id)
    _commit(db, "Mã hóa đơn hoặc đơn hàng đã có hóa đơn.")
    db.refresh(invoice)
    return invoice


@router.put("/invoices/{invoice_id}", response_model=InvoiceOut)
def update_invoice(invoice_id: int, data: InvoiceWrite, db: DbSession, user: CurrentUser) -> Invoice:
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT)
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Không tìm thấy hóa đơn.")
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(409, "Chỉ hóa đơn nháp mới được cập nhật.")
    if data.status not in (InvoiceStatus.DRAFT, InvoiceStatus.ISSUED):
        raise HTTPException(422, "Hóa đơn chỉ được chuyển từ nháp sang đã phát hành.")
    order = db.get(ProductionOrder, data.order_id)
    if order is None:
        raise HTTPException(422, "Đơn hàng không tồn tại.")
    if db.scalar(
        select(Invoice.id).where(Invoice.order_id == data.order_id, Invoice.id != invoice.id).limit(1)
    ) is not None:
        raise HTTPException(409, "Đơn hàng này đã có hóa đơn khác. Hãy chọn đơn chưa lập hóa đơn.")
    subtotal = Decimal(order.quantity) * data.service_unit_price
    if data.discount_amount > subtotal:
        raise HTTPException(422, "Chiết khấu không được lớn hơn thành tiền.")
    invoice.invoice_code = data.invoice_code
    invoice.order_id = data.order_id
    invoice.service_unit_price = data.service_unit_price
    invoice.discount_amount = data.discount_amount
    invoice.subtotal = subtotal
    invoice.total_amount = subtotal - data.discount_amount
    invoice.status = data.status
    if data.status == InvoiceStatus.ISSUED:
        invoice.issued_at = datetime.now(timezone.utc)
    _audit(db, user, "update", "invoice", invoice.id)
    _commit(db, "Mã hóa đơn hoặc đơn hàng đã được sử dụng.")
    db.refresh(invoice)
    return invoice


@router.post("/payments", response_model=PaymentOut, status_code=201)
def create_payment(data: PaymentWrite, db: DbSession, user: CurrentUser) -> Payment:
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT)
    invoice = db.get(Invoice, data.invoice_id)
    if invoice is None or invoice.status in (InvoiceStatus.DRAFT, InvoiceStatus.VOID):
        raise HTTPException(422, "Hóa đơn không tồn tại hoặc chưa được phát hành.")
    invoice = db.scalar(select(Invoice).where(Invoice.id == data.invoice_id).with_for_update())
    if data.amount > invoice.total_amount - invoice.amount_paid:
        raise HTTPException(422, "Số tiền thanh toán vượt quá số còn phải thu.")
    invoice.amount_paid += data.amount
    invoice.status = (
        InvoiceStatus.PAID if invoice.amount_paid == invoice.total_amount else InvoiceStatus.PARTIALLY_PAID
    )
    payment = Payment(**data.model_dump(), received_by_id=user.id)
    db.add(payment)
    db.flush()
    _audit(db, user, "create", "payment", payment.id)
    _commit(db, "Không thể ghi nhận thanh toán.")
    db.refresh(payment)
    return payment


@router.get("/payments", response_model=list[PaymentOut])
def list_payments(db: DbSession, user: CurrentUser, invoice_id: int | None = None):
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT)
    query = select(Payment)
    if invoice_id is not None:
        query = query.where(Payment.invoice_id == invoice_id)
    return list(db.scalars(query.order_by(Payment.received_at.desc()).limit(500)).all())


@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(db: DbSession, user: CurrentUser):
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT)
    return list(db.scalars(select(Expense).order_by(Expense.spent_at.desc()).limit(500)).all())


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(data: ExpenseWrite, db: DbSession, user: CurrentUser) -> Expense:
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT)
    _validate_refs(db, **{"Đơn hàng": (ProductionOrder, data.order_id)})
    expense = Expense(**data.model_dump(), recorded_by_id=user.id)
    db.add(expense)
    db.flush()
    _audit(db, user, "create", "expense", expense.id)
    _commit(db, "Không thể ghi nhận chi phí.")
    db.refresh(expense)
    return expense


@router.put("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, data: ExpenseWrite, db: DbSession, user: CurrentUser) -> Expense:
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT)
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(404, "Không tìm thấy khoản chi.")
    _validate_refs(db, **{"Đơn hàng": (ProductionOrder, data.order_id)})
    for key, value in data.model_dump().items():
        setattr(expense, key, value)
    _audit(db, user, "update", "expense", expense.id)
    _commit(db, "Không thể cập nhật khoản chi.")
    db.refresh(expense)
    return expense


@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db: DbSession, user: CurrentUser) -> None:
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT)
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(404, "Không tìm thấy khoản chi.")
    db.delete(expense)
    _audit(db, user, "delete", "expense", expense_id)
    _commit(db, "Không thể xóa khoản chi.")


@router.get("/reports/financial", response_model=FinancialReportOut)
def financial_report(
    db: DbSession,
    user: CurrentUser,
    start_date: date | None = None,
    end_date: date | None = None,
) -> FinancialReportOut:
    ensure_roles(user, *MANAGERS, UserRole.ACCOUNTANT)
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, "Ngày kết thúc phải bằng hoặc sau ngày bắt đầu.")

    invoices_query = select(Invoice).where(
        Invoice.status.in_((InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.PAID))
    )
    expenses_query = select(Expense)
    start_at = datetime.combine(start_date, time.min, tzinfo=timezone.utc) if start_date else None
    end_at = datetime.combine(end_date, time.min, tzinfo=timezone.utc) if end_date else None
    if start_at:
        invoices_query = invoices_query.where(Invoice.issued_at >= start_at)
        expenses_query = expenses_query.where(Expense.spent_at >= start_at)
    if end_at:
        end_exclusive = end_at + timedelta(days=1)
        invoices_query = invoices_query.where(Invoice.issued_at < end_exclusive)
        expenses_query = expenses_query.where(Expense.spent_at < end_exclusive)

    invoice_values = db.execute(
        select(
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.total_amount), 0),
            func.coalesce(func.sum(Invoice.amount_paid), 0),
        ).where(Invoice.id.in_(invoices_query.with_only_columns(Invoice.id)))
    ).one()
    expense_total = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.id.in_(expenses_query.with_only_columns(Expense.id))
        )
    ) or Decimal(0)
    billed = Decimal(invoice_values[1])
    collected = Decimal(invoice_values[2])
    return FinancialReportOut(
        start_date=start_date,
        end_date=end_date,
        invoice_count=invoice_values[0],
        billed_amount=billed,
        collected_amount=collected,
        outstanding_amount=billed - collected,
        expense_total=Decimal(expense_total),
        net_collected=collected - Decimal(expense_total),
    )
