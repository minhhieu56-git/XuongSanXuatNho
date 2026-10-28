from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.migrations import upgrade_schema
from app.core.security import hash_password
from app.models import (
    BOMItem,
    Customer,
    InventoryItem,
    Invoice,
    Machine,
    ProductionLine,
    ProductionOperation,
    ProductionLog,
    ProductionOrder,
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
)


def seed() -> None:
    upgrade_schema()
    with SessionLocal() as db:
        demo_accounts = [
            ("admin@example.com", "Quản trị viên", UserRole.ADMIN),
            ("manager@example.com", "Quản lý xưởng", UserRole.MANAGER),
            ("worker@example.com", "Nhân viên xưởng", UserRole.WORKER),
            ("accountant@example.com", "Kế toán", UserRole.ACCOUNTANT),
            ("customer@example.com", "Khách hàng demo", UserRole.CUSTOMER),
        ]
        users: dict[str, User] = {}
        for email, full_name, role in demo_accounts:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password("ChangeMe123!"),
                    role=role,
                )
                db.add(user)
                db.flush()
            users[email] = user
        admin = users["admin@example.com"]
        worker_user = users["worker@example.com"]
        customer_user = users["customer@example.com"]
        materials = [
            InventoryItem(sku="MAT-STEEL-01", name="Thép tấm", unit="kg", quantity=Decimal("120"), minimum_quantity=Decimal("50"), unit_cost=Decimal("25000")),
            InventoryItem(sku="MAT-BOLT-02", name="Bu lông M8", unit="cái", quantity=Decimal("35"), minimum_quantity=Decimal("100"), unit_cost=Decimal("1200")),
            InventoryItem(sku="MAT-PAINT-03", name="Sơn phủ", unit="lít", quantity=Decimal("80"), minimum_quantity=Decimal("20"), unit_cost=Decimal("95000")),
        ]
        for item in materials:
            if db.scalar(select(InventoryItem).where(InventoryItem.sku == item.sku)) is None:
                db.add(item)
        db.flush()
        worker = db.scalar(select(Worker).where(Worker.worker_code == "W-DEMO"))
        if worker is None:
            worker = Worker(worker_code="W-DEMO", full_name="Nhân viên xưởng", user_id=worker_user.id)
            db.add(worker)
        elif worker.user_id is None:
            worker.user_id = worker_user.id
        line = db.scalar(select(ProductionLine).where(ProductionLine.line_code == "LINE-DEMO"))
        if line is None:
            line = ProductionLine(line_code="LINE-DEMO", name="Dây chuyền gia công", location="Khu A")
            db.add(line)
        shift = db.scalar(select(Shift).where(Shift.name == "Ca hành chính"))
        if shift is None:
            shift = Shift(name="Ca hành chính", start_time=time(8), end_time=time(17))
            db.add(shift)
        db.flush()
        machine = db.scalar(select(Machine).where(Machine.machine_code == "M-DEMO"))
        if machine is None:
            machine = Machine(
                machine_code="M-DEMO", name="Máy cắt mẫu", line_id=line.id, status=MachineStatus.AVAILABLE
            )
            db.add(machine)
        customer = db.scalar(select(Customer).where(Customer.customer_code == "CUS-DEMO"))
        if customer is None:
            customer = Customer(
                customer_code="CUS-DEMO", full_name="Khách hàng demo", user_id=customer_user.id
            )
            db.add(customer)
        db.flush()
        if db.scalar(select(ProductionOrder).where(ProductionOrder.order_code == "PX-2026-001")) is None:
            steel = db.scalar(select(InventoryItem).where(InventoryItem.sku == "MAT-STEEL-01"))
            bolt = db.scalar(select(InventoryItem).where(InventoryItem.sku == "MAT-BOLT-02"))
            if steel is not None and bolt is not None:
                db.add_all(
                    [
                        ProductionOrder(
                            order_code="PX-2026-001",
                            product_name="Kệ công nghiệp",
                            quantity=40,
                            status=OrderStatus.IN_PROGRESS,
                            due_date=datetime.now(timezone.utc) + timedelta(days=4),
                            material_id=steel.id,
                            created_by_id=admin.id,
                        ),
                        ProductionOrder(
                            order_code="PX-2026-002",
                            product_name="Bàn thao tác",
                            quantity=15,
                            status=OrderStatus.PLANNED,
                            due_date=datetime.now(timezone.utc) + timedelta(days=8),
                            material_id=bolt.id,
                            created_by_id=admin.id,
                        ),
                        ProductionOrder(
                            order_code="PX-2026-003",
                            product_name="Tủ dụng cụ",
                            quantity=8,
                            status=OrderStatus.COMPLETED,
                            due_date=datetime.now(timezone.utc) - timedelta(days=1),
                            material_id=steel.id,
                            created_by_id=admin.id,
                        ),
                    ]
                )
                db.flush()
        steel = db.scalar(select(InventoryItem).where(InventoryItem.sku == "MAT-STEEL-01"))
        if steel is not None and db.scalar(
            select(BOMItem).where(
                BOMItem.product_name == "Kệ công nghiệp", BOMItem.material_id == steel.id
            )
        ) is None:
            db.add(BOMItem(product_name="Kệ công nghiệp", material_id=steel.id, quantity_per_unit=Decimal("2.5000")))
        if steel is not None and db.scalar(
            select(ProductionOperation).where(
                ProductionOperation.order_id == db.scalar(
                    select(ProductionOrder.id).where(ProductionOrder.order_code == "PX-2026-001")
                ),
                ProductionOperation.sequence == 1,
            )
        ) is None:
            demo_order_id = db.scalar(
                select(ProductionOrder.id).where(ProductionOrder.order_code == "PX-2026-001")
            )
            if demo_order_id is not None:
                db.add_all(
                    [
                        ProductionOperation(
                            order_id=demo_order_id,
                            stage_name="Cắt vật liệu",
                            sequence=1,
                            status=OperationStatus.IN_PROGRESS,
                            instructions="Kiểm tra bản vẽ và quy trình an toàn trước khi vận hành.",
                        ),
                        ProductionOperation(
                            order_id=demo_order_id,
                            stage_name="Lắp ráp",
                            sequence=2,
                            status=OperationStatus.PLANNED,
                        ),
                    ]
                )
        completed_order = db.scalar(
            select(ProductionOrder).where(ProductionOrder.order_code == "PX-2026-003")
        )
        if completed_order is not None and completed_order.customer_id is None:
            completed_order.customer_id = customer.id
        if completed_order is not None and db.scalar(
            select(Invoice).where(Invoice.invoice_code == "INV-2026-003")
        ) is None:
            total = Decimal(completed_order.quantity) * Decimal("100000")
            db.add(
                Invoice(
                    invoice_code="INV-2026-003",
                    order_id=completed_order.id,
                    service_unit_price=Decimal("100000"),
                    discount_amount=Decimal("0"),
                    subtotal=total,
                    total_amount=total,
                    amount_paid=Decimal("0"),
                    status=InvoiceStatus.ISSUED,
                    issued_at=datetime.now(timezone.utc),
                    created_by_id=admin.id,
                )
            )
        demo_order = db.scalar(select(ProductionOrder).where(ProductionOrder.order_code == "PX-2026-001"))
        if demo_order is not None and demo_order.customer_id is None:
            demo_order.customer_id = customer.id
        operation = db.scalar(
            select(ProductionOperation).where(
                ProductionOperation.order_id == demo_order.id if demo_order else False,
                ProductionOperation.sequence == 1,
            )
        )
        if demo_order is not None and operation is not None and not db.scalar(
            select(ProductionLog.id).where(ProductionLog.order_id == demo_order.id)
        ):
            now = datetime.now(timezone.utc)
            db.add(
                ProductionLog(
                    order_id=demo_order.id,
                    operation_id=operation.id,
                    worker_id=worker.id,
                    machine_id=machine.id,
                    shift_id=shift.id,
                    good_quantity=5,
                    rejected_quantity=1,
                    incident_type="Kiểm tra mẫu",
                    notes="Đã cách ly sản phẩm lỗi để kiểm tra.",
                    logged_by_id=worker_user.id,
                    logged_at=now,
                )
            )
        if demo_order is not None and not db.scalar(
            select(WorkSchedule.id).where(
                WorkSchedule.order_id == demo_order.id,
                WorkSchedule.worker_id == worker.id,
            )
        ):
            starts_at = datetime.now(timezone.utc) + timedelta(hours=2)
            db.add(
                WorkSchedule(
                    order_id=demo_order.id,
                    worker_id=worker.id,
                    machine_id=machine.id,
                    line_id=line.id,
                    shift_id=shift.id,
                    starts_at=starts_at,
                    ends_at=starts_at + timedelta(hours=1),
                    status=ScheduleStatus.SCHEDULED,
                    created_by_id=admin.id,
                )
            )
        db.commit()
    print("Seed hoàn tất. Tài khoản demo: admin/manager/worker@example.com / ChangeMe123!")


if __name__ == "__main__":
    seed()
