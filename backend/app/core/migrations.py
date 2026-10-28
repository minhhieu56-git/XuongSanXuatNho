from sqlalchemy import inspect, text

from app.core.database import Base, engine
from app import models as _models


def upgrade_schema() -> None:
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'ACCOUNTANT'"))
            connection.execute(text("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'CUSTOMER'"))
            connection.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")
            )

    Base.metadata.create_all(bind=engine)

    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE production_orders "
                    "ADD COLUMN IF NOT EXISTS customer_id INTEGER "
                    "REFERENCES customers(id) ON DELETE SET NULL"
                )
            )
            existing_checks = {
                constraint["name"] for constraint in inspect(connection).get_check_constraints("invoices")
            }
            invoice_checks = {
                "ck_invoice_subtotal_nonnegative": "subtotal >= 0",
                "ck_invoice_total_nonnegative": "total_amount >= 0",
                "ck_invoice_paid_in_range": "amount_paid >= 0 AND amount_paid <= total_amount",
            }
            for name, condition in invoice_checks.items():
                if name not in existing_checks:
                    connection.execute(
                        text(
                            f"ALTER TABLE invoices ADD CONSTRAINT {name} "
                            f"CHECK ({condition}) NOT VALID"
                        )
                    )
                    connection.execute(text(f"ALTER TABLE invoices VALIDATE CONSTRAINT {name}"))
    else:
        inspector = inspect(engine)
        if "is_active" not in {column["name"] for column in inspector.get_columns("users")}:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")
                )
