const API_URL = import.meta.env.VITE_API_URL ?? "/api";

export type User = { id: number; email: string; full_name: string; role: "admin" | "manager" | "worker" | "accountant" | "customer" };
export type InventoryItem = {
  id: number; sku: string; name: string; unit: string; quantity: number;
  minimum_quantity: number; unit_cost: number; updated_at: string;
};
export type Order = {
  id: number; order_code: string; product_name: string; quantity: number; status: string;
  due_date: string | null; notes: string | null; material_id: number | null; created_at: string;
  material?: Pick<InventoryItem, "id" | "sku" | "name" | "unit"> | null;
};
export type Dashboard = {
  order_count: number; active_order_count: number; completed_order_count: number;
  low_stock_count: number; inventory_value: number; recent_orders: Order[];
};

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

export async function request<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail ?? "Không thể hoàn thành yêu cầu.", response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<{ access_token: string; user: User }> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new Error("Không kết nối được máy chủ ứng dụng. Hãy kiểm tra backend đã chạy và thử tải lại trang.");
  }
  if (!response.ok) {
    let detail = "Đăng nhập thất bại.";
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      detail = `Máy chủ trả lỗi HTTP ${response.status}. Hãy kiểm tra backend đang chạy đúng dự án.`;
    }
    throw new ApiError(detail, response.status);
  }
  return response.json();
}
