import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models import User
from app.models.entities import UserRole


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with test_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with test_session() as session:
        session.add_all(
            [
                User(
                    email="admin@example.com",
                    full_name="Test Admin",
                    password_hash=hash_password("ChangeMe123!"),
                    role=UserRole.ADMIN,
                ),
                User(
                    email="worker@example.com",
                    full_name="Test Worker",
                    password_hash=hash_password("ChangeMe123!"),
                    role=UserRole.WORKER,
                ),
            ]
            )
        session.commit()
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "missing@example.com", "password": "WrongPassword1"},
    )
    assert response.status_code == 401


def test_login_validates_email_and_password_length(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"email": "bad", "password": "short"})
    assert response.status_code == 422


def test_login_returns_token_for_valid_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMe123!"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"
    assert response.json()["access_token"]


def test_protected_endpoint_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/dashboard")
    assert response.status_code == 401


def test_invalid_order_quantity_is_rejected(client: TestClient) -> None:
    token = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMe123!"},
    ).json()["access_token"]
    response = client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "order_code": "PX-X",
            "product_name": "Sản phẩm",
            "quantity": 0,
        },
    )
    assert response.status_code == 422


def test_authenticated_dashboard_returns_empty_summary(client: TestClient) -> None:
    token = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMe123!"},
    ).json()["access_token"]
    response = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["order_count"] == 0


def test_worker_cannot_create_inventory(client: TestClient) -> None:
    token = client.post(
        "/api/auth/login",
        json={"email": "worker@example.com", "password": "ChangeMe123!"},
    ).json()["access_token"]
    response = client.post(
        "/api/inventory",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sku": "MAT-TEST",
            "name": "Thép thử",
            "unit": "kg",
            "quantity": 10,
            "minimum_quantity": 2,
            "unit_cost": 1000,
        },
    )
    assert response.status_code == 403


def test_manager_can_create_update_search_and_delete_inventory(client: TestClient) -> None:
    token = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMe123!"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "sku": "MAT-TEST",
        "name": "Thép thử",
        "unit": "kg",
        "quantity": 10,
        "minimum_quantity": 2,
        "unit_cost": 1000,
    }
    created = client.post("/api/inventory", headers=headers, json=payload)
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert client.get("/api/inventory?search=MAT-TEST", headers=headers).json()[0]["id"] == item_id

    payload["quantity"] = 20
    updated = client.put(f"/api/inventory/{item_id}", headers=headers, json=payload)
    assert updated.status_code == 200
    assert updated.json()["quantity"] == 20
    assert client.delete(f"/api/inventory/{item_id}", headers=headers).status_code == 204
    assert client.get("/api/inventory?search=MAT-TEST", headers=headers).json() == []


def test_manager_can_create_update_search_and_delete_order(client: TestClient) -> None:
    token = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMe123!"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "order_code": "PX-TEST-01",
        "product_name": "Kệ thử nghiệm",
        "quantity": 3,
        "status": "planned",
    }
    created = client.post("/api/orders", headers=headers, json=payload)
    assert created.status_code == 201
    order_id = created.json()["id"]
    assert client.get("/api/orders?search=PX-TEST", headers=headers).json()[0]["id"] == order_id

    payload["status"] = "in_progress"
    updated = client.put(f"/api/orders/{order_id}", headers=headers, json=payload)
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    assert client.delete(f"/api/orders/{order_id}", headers=headers).status_code == 204
    assert client.get("/api/orders?search=PX-TEST", headers=headers).json() == []


def test_ai_falls_back_to_local_analysis_without_api_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.gemini.settings.gemini_api_key", "")
    token = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMe123!"},
    ).json()["access_token"]
    response = client.post(
        "/api/ai/analysis",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Tóm tắt tình hình kho hiện tại."},
    )
    assert response.status_code == 200
    assert response.json()["provider"] == "local"
    assert "không phải phân tích từ mô hình Gemini" in response.json()["answer"]


def test_local_ai_analysis_reports_low_stock_items(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.gemini.settings.gemini_api_key", "")
    token = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMe123!"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/inventory",
        headers=headers,
        json={
            "sku": "MAT-LOW",
            "name": "Thép thiếu tồn",
            "unit": "kg",
            "quantity": 2,
            "minimum_quantity": 10,
            "unit_cost": 1000,
        },
    )
    assert created.status_code == 201
    response = client.post(
        "/api/ai/analysis",
        headers=headers,
        json={"question": "Vật tư nào đang dưới ngưỡng tồn?"},
    )
    assert response.status_code == 200
    assert "Thép thiếu tồn (MAT-LOW)" in response.json()["answer"]
    assert "thiếu ít nhất 8 kg" in response.json()["answer"]


@pytest.mark.parametrize(
    ("provider_status", "expected_status", "expected_detail"),
    [
        (404, 502, "GEMINI_MODEL"),
        (503, 503, "quá tải"),
    ],
)
def test_ai_reports_actionable_gemini_errors(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    provider_status: int,
    expected_status: int,
    expected_detail: str,
) -> None:
    monkeypatch.setattr("app.services.gemini.settings.gemini_api_key", "test-key")

    async def fake_post(self, url, *, params, json):
        request = httpx.Request("POST", url)
        return httpx.Response(
            provider_status,
            request=request,
            json={"error": {"status": "MODEL_ERROR", "message": "provider detail"}},
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    token = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMe123!"},
    ).json()["access_token"]
    response = client.post(
        "/api/ai/analysis",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Tóm tắt tình hình kho hiện tại."},
    )
    assert response.status_code == expected_status
    assert expected_detail in response.json()["detail"]
