from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import InventoryItem, ProductionOrder, User
from app.models.entities import OrderStatus, UserRole


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        demo_accounts = [
            ("admin@example.com", "Quản trị viên", UserRole.ADMIN),
            ("manager@example.com", "Quản lý xưởng", UserRole.MANAGER),
            ("worker@example.com", "Nhân viên xưởng", UserRole.WORKER),
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
        materials = [
            InventoryItem(sku="MAT-STEEL-01", name="Thép tấm", unit="kg", quantity=Decimal("120"), minimum_quantity=Decimal("50"), unit_cost=Decimal("25000")),
            InventoryItem(sku="MAT-BOLT-02", name="Bu lông M8", unit="cái", quantity=Decimal("35"), minimum_quantity=Decimal("100"), unit_cost=Decimal("1200")),
            InventoryItem(sku="MAT-PAINT-03", name="Sơn phủ", unit="lít", quantity=Decimal("80"), minimum_quantity=Decimal("20"), unit_cost=Decimal("95000")),
        ]
        for item in materials:
            if db.scalar(select(InventoryItem).where(InventoryItem.sku == item.sku)) is None:
                db.add(item)
        db.flush()
        if db.scalar(select(ProductionOrder).where(ProductionOrder.order_code == "PX-2026-001")) is None:
            steel = db.scalar(select(InventoryItem).where(InventoryItem.sku == "MAT-STEEL-01"))
            bolt = db.scalar(select(InventoryItem).where(InventoryItem.sku == "MAT-BOLT-02"))
            db.add_all(
                [
                    ProductionOrder(order_code="PX-2026-001", product_name="Kệ công nghiệp", quantity=40, status=OrderStatus.IN_PROGRESS, due_date=datetime.now(timezone.utc) + timedelta(days=4), material_id=steel.id, created_by_id=admin.id),
                    ProductionOrder(order_code="PX-2026-002", product_name="Bàn thao tác", quantity=15, status=OrderStatus.PLANNED, due_date=datetime.now(timezone.utc) + timedelta(days=8), material_id=bolt.id, created_by_id=admin.id),
                    ProductionOrder(order_code="PX-2026-003", product_name="Tủ dụng cụ", quantity=8, status=OrderStatus.COMPLETED, due_date=datetime.now(timezone.utc) - timedelta(days=1), material_id=steel.id, created_by_id=admin.id),
                ]
            )
        db.commit()
    print("Seed hoàn tất. Tài khoản demo: admin/manager/worker@example.com / ChangeMe123!")


if __name__ == "__main__":
    seed()
