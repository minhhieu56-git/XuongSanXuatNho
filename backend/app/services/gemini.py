import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import InventoryItem, ProductionOrder
from app.models.entities import OrderStatus

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "operations_system.txt").read_text(encoding="utf-8")


def build_context(db: Session) -> dict[str, object]:
    inventory = db.scalars(select(InventoryItem).order_by(InventoryItem.name)).all()
    orders = db.scalars(
        select(ProductionOrder).where(ProductionOrder.status != OrderStatus.CANCELLED)
        .order_by(ProductionOrder.due_date)
    ).all()
    return {
        "inventory": [
            {
                "sku": item.sku,
                "name": item.name,
                "unit": item.unit,
                "quantity": float(item.quantity),
                "minimum_quantity": float(item.minimum_quantity),
                "unit_cost": float(item.unit_cost),
                "is_low_stock": item.quantity <= item.minimum_quantity,
            }
            for item in inventory
        ],
        "production_orders": [
            {
                "order_code": order.order_code,
                "product_name": order.product_name,
                "quantity": order.quantity,
                "status": order.status.value,
                "due_date": order.due_date.isoformat() if order.due_date else None,
                "material": order.material.name if order.material else None,
            }
            for order in orders
        ],
    }


def analyze_locally(db: Session) -> dict[str, object]:
    context = build_context(db)
    low_stock = [
        item for item in context["inventory"]
        if item["is_low_stock"]
    ]
    now = datetime.now(timezone.utc)
    active_orders = [
        order for order in context["production_orders"]
        if order["status"] in (OrderStatus.PLANNED.value, OrderStatus.IN_PROGRESS.value)
    ]

    def due_date(order: dict[str, object]) -> datetime | None:
        raw_date = order["due_date"]
        if not isinstance(raw_date, str):
            return None
        parsed_date = datetime.fromisoformat(raw_date)
        return parsed_date.replace(tzinfo=timezone.utc) if parsed_date.tzinfo is None else parsed_date

    active_orders.sort(key=lambda order: due_date(order) or datetime.max.replace(tzinfo=timezone.utc))
    lines = ["Tóm tắt", f"- Có {len(low_stock)} mặt hàng dưới hoặc bằng mức tồn tối thiểu."]
    if active_orders:
        lines.append(f"- Có {len(active_orders)} đơn chưa hoàn tất cần theo dõi.")
    else:
        lines.append("- Hiện không có đơn đang sản xuất hoặc chờ thực hiện.")

    lines.append("\nNhận định dựa trên dữ liệu")
    if low_stock:
        for item in low_stock:
            shortfall = max(item["minimum_quantity"] - item["quantity"], 0)
            lines.append(
                f"- {item['name']} ({item['sku']}): còn {item['quantity']:g} {item['unit']}, "
                f"mức tối thiểu {item['minimum_quantity']:g} {item['unit']}; "
                f"thiếu ít nhất {shortfall:g} {item['unit']} để đạt ngưỡng."
            )
    else:
        lines.append("- Không có vật tư nào ở dưới ngưỡng tồn tối thiểu.")

    lines.append("\nĐề xuất")
    if low_stock:
        lines.append("- Kiểm tra nhu cầu sản xuất và lập kế hoạch bổ sung các vật tư đang thấp; xác nhận số lượng trước khi đặt mua.")
    else:
        lines.append("- Tiếp tục theo dõi tồn kho theo ngưỡng hiện tại.")
    if active_orders:
        for order in active_orders[:5]:
            due = due_date(order)
            if due is None:
                due_label = "chưa đặt hạn hoàn thành"
            else:
                days_left = (due.date() - now.date()).days
                due_label = "đã quá hạn" if days_left < 0 else (
                    "hạn hôm nay" if days_left == 0 else f"còn {days_left} ngày"
                )
            lines.append(
                f"- Theo dõi đơn {order['order_code']} – {order['product_name']} "
                f"({status_label(order['status'])}; {due_label})."
            )

    lines.append(
        "\nGiới hạn\n"
        "- Đây là kiểm tra theo quy tắc từ tồn kho và đơn hàng hiện có, không phải phân tích từ mô hình Gemini. "
        "Hệ thống chưa có định mức nguyên liệu, lịch sử tiêu thụ hoặc công suất để dự báo nhu cầu."
    )
    return {
        "answer": "\n".join(lines),
        "model": "Phân tích quy tắc nội bộ",
        "provider": "local",
        "generated_at": now,
        "data_scope": f"{len(context['production_orders'])} đơn hàng và {len(context['inventory'])} mặt hàng tồn kho",
    }


def status_label(value: object) -> str:
    return {
        OrderStatus.PLANNED.value: "đã lên kế hoạch",
        OrderStatus.IN_PROGRESS.value: "đang sản xuất",
    }.get(value, str(value))


async def analyze_operations(db: Session, question: str) -> dict[str, object]:
    if not settings.gemini_api_key:
        return analyze_locally(db)
    context = build_context(db)
    user_prompt = (
        "Câu hỏi của quản lý:\n"
        f"{question}\n\nDữ liệu vận hành hiện tại (JSON, chỉ đọc):\n"
        f"{json.dumps(context, ensure_ascii=False)}"
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1200},
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
            response = await client.post(url, params={"key": settings.gemini_api_key}, json=payload)
        if response.status_code == 429:
            raise HTTPException(429, "Gemini đang giới hạn yêu cầu. Vui lòng thử lại sau.")
        response.raise_for_status()
        result = response.json()
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Gemini phản hồi quá thời gian cho phép.") from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (500, 502, 503, 504):
            raise HTTPException(503, "Gemini đang quá tải hoặc tạm thời không khả dụng. Vui lòng thử lại sau.") from exc
        if exc.response.status_code in (401, 403):
            raise HTTPException(502, "Gemini từ chối API key. Kiểm tra key và quyền truy cập Gemini API.") from exc
        if exc.response.status_code in (400, 404):
            raise HTTPException(502, "Model Gemini hoặc cấu hình yêu cầu không còn khả dụng. Kiểm tra GEMINI_MODEL.") from exc
        raise HTTPException(502, "Không thể kết nối dịch vụ Gemini. Hãy kiểm tra cấu hình và thử lại.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Phản hồi Gemini không hợp lệ hoặc không thể truy cập dịch vụ.") from exc

    if not isinstance(result, dict):
        raise HTTPException(502, "Gemini trả về dữ liệu không đúng định dạng.")
    candidates = result.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        raise HTTPException(502, "Gemini không trả về kết quả phân tích hợp lệ.")
    content = candidates[0].get("content")
    parts = content.get("parts", []) if isinstance(content, dict) else []
    if not isinstance(parts, list):
        raise HTTPException(502, "Gemini trả về dữ liệu không đúng định dạng.")
    answer = "\n".join(
        part["text"] for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ).strip()
    if not answer:
        raise HTTPException(502, "Gemini trả về nội dung rỗng. Vui lòng thử lại.")
    return {
        "answer": answer,
        "model": settings.gemini_model,
        "provider": "gemini",
        "generated_at": datetime.now(timezone.utc),
        "data_scope": f"{len(context['production_orders'])} đơn hàng và {len(context['inventory'])} mặt hàng tồn kho",
    }
