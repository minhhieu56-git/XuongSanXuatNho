import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Check, Pencil, Plus, RefreshCw, Trash2, X } from "lucide-react";
import { ApiError, request, type User } from "./api";

type Field = {
  key: string;
  label: string;
  type?: "number" | "date" | "time" | "datetime-local" | "textarea" | "checkbox" | "select" | "password";
  optional?: boolean;
  defaultValue?: string;
  placeholder?: string;
  options?: string[];
  optionItems?: {value: string; label: string}[];
};
type Resource = {
  path: string;
  title: string;
  fields: Field[];
  columns: string[];
  roles: User["role"][];
  createRoles?: User["role"][];
  update?: boolean;
  remove?: boolean;
  updateRoles?: User["role"][];
  removeRoles?: User["role"][];
  readOnly?: boolean;
};
type Row = Record<string, unknown> & { id: number };
type FinancialReport = {invoice_count: number; billed_amount: number; collected_amount: number; outstanding_amount: number; expense_total: number; net_collected: number};

const managers: User["role"][] = ["admin", "manager"];
const productionStaff: User["role"][] = [...managers, "worker"];
const financeStaff: User["role"][] = [...managers, "accountant"];
const resources: Record<string, Resource> = {
  users: {
    path: "admin/users", title: "Tài khoản", roles: ["admin"], createRoles: ["admin"], update: true, updateRoles: ["admin"], remove: true, removeRoles: ["admin"],
    fields: [
      { key: "email", label: "Email", placeholder: "Ví dụ: nhanvien@example.com" },
      { key: "full_name", label: "Họ tên", placeholder: "Ví dụ: Nguyễn Văn An" },
      { key: "password", label: "Mật khẩu (tối thiểu 12 ký tự)", type: "password", optional: true },
      { key: "role", label: "Vai trò", type: "select", options: ["admin", "manager", "worker", "accountant", "customer"] },
      { key: "is_active", label: "Đang hoạt động", type: "checkbox" },
    ], columns: ["email", "full_name", "role", "is_active"],
  },
  audit: {
    path: "admin/audit-logs", title: "Nhật ký kiểm toán", roles: ["admin"], readOnly: true,
    fields: [], columns: ["created_at", "user_id", "action", "entity_type", "entity_id", "details"],
  },
  workers: {
    path: "workers", title: "Công nhân", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "worker_code", label: "Mã công nhân", placeholder: "Ví dụ: CN-001" },
      { key: "full_name", label: "Họ tên", placeholder: "Ví dụ: Nguyễn Văn An" },
      { key: "phone", label: "Điện thoại", optional: true, placeholder: "Ví dụ: 0901234567" },
      { key: "skill", label: "Kỹ năng", optional: true, placeholder: "Ví dụ: Vận hành máy cắt" },
      { key: "status", label: "Trạng thái", type: "select", options: ["active", "inactive"] },
      { key: "user_id", label: "ID tài khoản (nếu có)", type: "number", optional: true, placeholder: "Ví dụ: 3" },
    ], columns: ["worker_code", "full_name", "phone", "skill", "status"],
  },
  customers: {
    path: "customers", title: "Khách hàng", roles: financeStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "customer_code", label: "Mã khách hàng", placeholder: "Ví dụ: KH-001" },
      { key: "full_name", label: "Tên khách hàng", placeholder: "Ví dụ: Công ty Minh Phát" },
      { key: "phone", label: "Điện thoại", optional: true, placeholder: "Ví dụ: 0901234567" },
      { key: "email", label: "Email", optional: true, placeholder: "Ví dụ: lienhe@minhphat.vn" },
      { key: "shipping_address", label: "Địa chỉ", type: "textarea", optional: true, placeholder: "Ví dụ: 12 Nguyễn Trãi, Quận 1, TP.HCM" },
      { key: "user_id", label: "ID tài khoản (nếu có)", type: "number", optional: true, placeholder: "Ví dụ: 5" },
    ], columns: ["customer_code", "full_name", "phone", "email"],
  },
  "production-lines": {
    path: "production-lines", title: "Dây chuyền", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "line_code", label: "Mã dây chuyền", placeholder: "Ví dụ: DL-01" },
      { key: "name", label: "Tên dây chuyền", placeholder: "Ví dụ: Dây chuyền lắp ráp A" },
      { key: "location", label: "Vị trí", optional: true, placeholder: "Ví dụ: Nhà xưởng số 1" },
      { key: "is_active", label: "Đang hoạt động", type: "checkbox" },
    ], columns: ["line_code", "name", "location", "is_active"],
  },
  machines: {
    path: "machines", title: "Máy móc", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "machine_code", label: "Mã máy", placeholder: "Ví dụ: MAY-001" },
      { key: "name", label: "Tên máy", placeholder: "Ví dụ: Máy cắt CNC" },
      { key: "line_id", label: "ID dây chuyền", type: "number", optional: true, placeholder: "Ví dụ: 1" },
      { key: "status", label: "Trạng thái", type: "select", options: ["available", "operating", "maintenance", "broken"] },
      { key: "technical_notes", label: "Ghi chú kỹ thuật", type: "textarea", optional: true, placeholder: "Ví dụ: Bảo dưỡng định kỳ mỗi 3 tháng" },
    ], columns: ["machine_code", "name", "line_id", "status"],
  },
  shifts: {
    path: "shifts", title: "Ca làm việc", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "name", label: "Tên ca", placeholder: "Ví dụ: Ca sáng" }, { key: "start_time", label: "Bắt đầu", type: "time" },
      { key: "end_time", label: "Kết thúc", type: "time" }, { key: "is_active", label: "Đang hoạt động", type: "checkbox" },
    ], columns: ["name", "start_time", "end_time", "is_active"],
  },
  schedules: {
    path: "schedules", title: "Lịch phân công", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "order_id", label: "ID đơn hàng", type: "number", placeholder: "Ví dụ: 12" },
      { key: "worker_id", label: "ID công nhân", type: "number", placeholder: "Ví dụ: 3" },
      { key: "machine_id", label: "ID máy", type: "number", placeholder: "Ví dụ: 2" },
      { key: "line_id", label: "ID dây chuyền", type: "number", optional: true, placeholder: "Ví dụ: 1" },
      { key: "shift_id", label: "ID ca", type: "number", optional: true, placeholder: "Ví dụ: 1" },
      { key: "starts_at", label: "Bắt đầu", type: "datetime-local" }, { key: "ends_at", label: "Kết thúc", type: "datetime-local" },
      { key: "status", label: "Trạng thái", type: "select", options: ["scheduled", "in_progress", "completed", "cancelled"] },
      { key: "notes", label: "Ghi chú", type: "textarea", optional: true, placeholder: "Ví dụ: Ưu tiên hoàn thành trong ca sáng" },
    ], columns: ["order_id", "worker_id", "machine_id", "starts_at", "ends_at", "status"],
  },
  bom: {
    path: "bom", title: "Định mức BOM", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "product_name", label: "Sản phẩm", placeholder: "Ví dụ: Bàn gỗ 120 cm" },
      { key: "material_id", label: "ID nguyên liệu", type: "number", placeholder: "Ví dụ: 4" },
      { key: "quantity_per_unit", label: "Định mức / sản phẩm", type: "number", placeholder: "Ví dụ: 0.5" },
      { key: "notes", label: "Ghi chú", type: "textarea", optional: true, placeholder: "Ví dụ: Hao hụt cho phép 2%" },
    ], columns: ["product_name", "material", "quantity_per_unit", "notes"],
  },
  "material-issues": {
    path: "material-issues", title: "Xuất vật tư theo BOM", roles: financeStaff,
    createRoles: managers,
    fields: [{ key: "order_id", label: "ID đơn hàng", type: "number", placeholder: "Ví dụ: 12" }],
    columns: ["order_id", "material_id", "quantity", "issued_by_id", "issued_at"],
  },
  operations: {
    path: "operations", title: "Công đoạn", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "order_id", label: "ID đơn hàng", type: "number", placeholder: "Ví dụ: 12" },
      { key: "stage_name", label: "Tên công đoạn", placeholder: "Ví dụ: Cắt phôi" },
      { key: "sequence", label: "Thứ tự", type: "number", placeholder: "Ví dụ: 1" },
      { key: "status", label: "Trạng thái", type: "select", options: ["planned", "in_progress", "completed", "blocked"] },
      { key: "completed_quantity", label: "Sản lượng đạt", type: "number", placeholder: "Ví dụ: 20" },
      { key: "rejected_quantity", label: "Sản lượng lỗi", type: "number", placeholder: "Ví dụ: 1" },
      { key: "instructions", label: "Hướng dẫn", type: "textarea", optional: true, placeholder: "Ví dụ: Kiểm tra kích thước trước khi chuyển công đoạn" },
    ], columns: ["order_id", "sequence", "stage_name", "status", "completed_quantity", "rejected_quantity"],
  },
  "production-logs": {
    path: "production-logs", title: "Nhật ký sản xuất", roles: productionStaff, createRoles: productionStaff,
    fields: [
      { key: "order_id", label: "ID đơn hàng", type: "number", placeholder: "Ví dụ: 12" },
      { key: "operation_id", label: "ID công đoạn", type: "number", optional: true, placeholder: "Ví dụ: 5" },
      { key: "worker_id", label: "ID công nhân", type: "number", optional: true, placeholder: "Ví dụ: 3" },
      { key: "machine_id", label: "ID máy", type: "number", optional: true, placeholder: "Ví dụ: 2" },
      { key: "shift_id", label: "ID ca", type: "number", optional: true, placeholder: "Ví dụ: 1" },
      { key: "good_quantity", label: "Sản phẩm đạt", type: "number", placeholder: "Ví dụ: 20" },
      { key: "rejected_quantity", label: "Sản phẩm lỗi", type: "number", placeholder: "Ví dụ: 1" },
      { key: "incident_type", label: "Loại sự cố", optional: true, placeholder: "Ví dụ: Máy dừng đột ngột" },
      { key: "notes", label: "Ghi chú", type: "textarea", optional: true, placeholder: "Ví dụ: Ca sáng, hoàn thành 20 sản phẩm; máy dừng 5 phút để xử lý." },
    ], columns: ["order_id", "operation_id", "good_quantity", "rejected_quantity", "incident_type", "logged_at"],
  },
  defects: {
    path: "defects", title: "Lỗi chất lượng", roles: productionStaff, createRoles: productionStaff, update: true, updateRoles: managers,
    fields: [
      { key: "order_id", label: "ID đơn hàng", type: "number", placeholder: "Ví dụ: 12" },
      { key: "operation_id", label: "ID công đoạn", type: "number", optional: true, placeholder: "Ví dụ: 5" },
      { key: "quantity", label: "Số lượng lỗi", type: "number", placeholder: "Ví dụ: 3" },
      { key: "defect_type", label: "Loại lỗi", placeholder: "Ví dụ: Sai kích thước" },
      { key: "description", label: "Mô tả", type: "textarea", optional: true, placeholder: "Ví dụ: 3 sản phẩm bị trầy mặt ngoài ở góc trái" },
      { key: "resolution", label: "Hướng xử lý", type: "textarea", optional: true, placeholder: "Ví dụ: Cách ly sản phẩm lỗi để kiểm tra lại" },
    ], columns: ["order_id", "quantity", "defect_type", "description", "reported_at"],
  },
  invoices: {
    path: "invoices", title: "Hóa đơn", roles: [...financeStaff, "customer"], createRoles: financeStaff, update: true, updateRoles: financeStaff,
    fields: [
      { key: "invoice_code", label: "Mã hóa đơn", placeholder: "Ví dụ: HD-2026-001" },
      { key: "order_id", label: "Đơn hàng chưa lập hóa đơn", type: "select" },
      { key: "service_unit_price", label: "Đơn giá", type: "number", placeholder: "Ví dụ: 150000" },
      { key: "discount_amount", label: "Chiết khấu", type: "number", optional: true, defaultValue: "0", placeholder: "Ví dụ: 50000" },
      { key: "status", label: "Trạng thái", type: "select", defaultValue: "draft", options: ["draft", "issued"] },
    ], columns: ["invoice_code", "order_id", "total_amount", "amount_paid", "status"],
  },
  payments: {
    path: "payments", title: "Thanh toán", roles: financeStaff,
    fields: [
      { key: "invoice_id", label: "ID hóa đơn", type: "number", placeholder: "Ví dụ: 3" },
      { key: "amount", label: "Số tiền", type: "number", placeholder: "Ví dụ: 500000" },
      { key: "method", label: "Phương thức", type: "select", options: ["cash", "bank_transfer"] },
      { key: "reference", label: "Mã tham chiếu", optional: true, placeholder: "Ví dụ: GD-2026-0001" },
    ], columns: ["invoice_id", "amount", "method", "reference", "received_at"],
  },
  expenses: {
    path: "expenses", title: "Chi phí", roles: financeStaff, createRoles: financeStaff, update: true, updateRoles: financeStaff, remove: true, removeRoles: financeStaff,
    fields: [
      { key: "description", label: "Nội dung", placeholder: "Ví dụ: Mua dầu bôi trơn máy cắt" },
      { key: "category", label: "Danh mục", placeholder: "Ví dụ: Bảo trì máy móc" },
      { key: "amount", label: "Số tiền", type: "number", placeholder: "Ví dụ: 250000" },
      { key: "order_id", label: "ID đơn hàng", type: "number", optional: true, placeholder: "Ví dụ: 12" },
      { key: "spent_at", label: "Thời điểm", type: "datetime-local" },
    ], columns: ["description", "category", "amount", "order_id", "spent_at"],
  },
};

const titles: Record<string, string> = Object.fromEntries(Object.entries(resources).map(([key, value]) => [key, value.title]));
const readable = (value: unknown) => typeof value === "boolean" ? (value ? "Có" : "Không")
  : value == null ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value);

export default function OperationsPanel({ token, user }: { token: string; user: User }) {
  const allowed = Object.entries(resources).filter(([, resource]) => resource.roles.includes(user.role));
  const [selected, setSelected] = useState(allowed[0]?.[0] ?? "workers");
  const resource = resources[selected] ?? resources.workers;
  const canCreate = Boolean(!resource.readOnly && (resource.createRoles
    ? resource.createRoles.includes(user.role)
    : resource.roles.includes(user.role)));
  const canUpdate = Boolean(resource.update && (resource.updateRoles?.includes(user.role) ?? resource.roles.includes(user.role)));
  const canRemove = Boolean(resource.remove && (resource.removeRoles?.includes(user.role) ?? resource.roles.includes(user.role)));
  const [rows, setRows] = useState<Row[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<Row | null>(null);
  const [invoiceOrderOptions, setInvoiceOrderOptions] = useState<{value: string; label: string}[]>([]);
  const [report, setReport] = useState<FinancialReport | null>(null);
  const showFinancialReport = managers.includes(user.role) || user.role === "accountant";
  const money = new Intl.NumberFormat("vi-VN", {style: "currency", currency: "VND", maximumFractionDigits: 0});

  const load = useCallback(async () => {
    if (!resource) return;
    setBusy(true);
    try {
      const [list, finance] = await Promise.all([
        request<Row[]>(`/${resource.path}`, token),
        showFinancialReport ? request<FinancialReport>("/reports/financial", token) : Promise.resolve(null),
      ]);
      setRows(list); setReport(finance);
      if (resource.path === "invoices" && canCreate) {
        const orders = await request<{id: number; order_code: string; product_name: string; quantity: number}[]>(
          "/orders",
          token,
        );
        const billedOrderIds = new Set(list.map(invoice => Number(invoice.order_id)));
        setInvoiceOrderOptions(orders
          .filter(order => !billedOrderIds.has(order.id))
          .map(order => ({
            value: String(order.id),
            label: `${order.order_code} · ${order.product_name} · ${order.quantity} sản phẩm`,
          })));
      } else {
        setInvoiceOrderOptions([]);
      }
      setError("");
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Không tải được dữ liệu.");
    } finally { setBusy(false); }
  }, [resource, token, showFinancialReport]);

  useEffect(() => { void load(); }, [load]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body: Record<string, unknown> = {};
    const isEditing = editing?.id != null;
    const formFields = resource.path === "admin/users" && isEditing
      ? resource.fields.filter(field => ["role", "is_active"].includes(field.key))
      : resource.path === "admin/users"
        ? resource.fields.filter(field => field.key !== "is_active")
        : resource.fields;
    for (const field of formFields) {
      const raw = form.get(field.key);
      if (field.type === "checkbox") body[field.key] = raw === "on";
      else if (resource.path === "invoices" && field.key === "discount_amount" && (raw === "" || raw == null)) body[field.key] = 0;
      else if (raw === "" || raw == null) body[field.key] = field.optional ? null : "";
      else if (field.type === "number") body[field.key] = Number(raw);
      else if (resource.path === "invoices" && field.key === "order_id") body[field.key] = Number(raw);
      else if (field.type === "datetime-local") body[field.key] = new Date(String(raw)).toISOString();
      else body[field.key] = String(raw);
    }
    setBusy(true); setError(""); setNotice("");
    try {
      if (resource.path === "material-issues") {
        await request(`/orders/${Number(body.order_id)}/materials/issue`, token, { method: "POST" });
        setNotice("Đã xuất vật tư theo BOM và cập nhật tồn kho.");
      } else {
        await request(`/${resource.path}${isEditing ? `/${editing.id}` : ""}`, token, {
          method: isEditing ? "PUT" : "POST", body: JSON.stringify(body),
        });
        setNotice("Đã lưu dữ liệu.");
      }
      setEditing(null); await load();
    } catch (issue) {
      setError(issue instanceof ApiError ? issue.message : issue instanceof Error ? issue.message : "Không lưu được dữ liệu.");
    } finally { setBusy(false); }
  }

  async function remove(row: Row) {
    const confirmation = resource.path === "admin/users"
      ? `Xóa vĩnh viễn tài khoản ${String(row.email)}? Nếu tài khoản đã phát sinh dữ liệu nghiệp vụ, hệ thống sẽ từ chối xóa; hãy vô hiệu hóa tài khoản trong phần Sửa.`
      : `Xóa bản ghi #${row.id}?`;
    if (!canRemove || !window.confirm(confirmation)) return;
    try {
      await request(`/${resource.path}/${row.id}`, token, { method: "DELETE" });
      setNotice("Đã xóa bản ghi."); await load();
    } catch (issue) { setError(issue instanceof Error ? issue.message : "Không xóa được dữ liệu."); }
  }

  function openCreateForm() {
    setError("");
    setNotice("");
    setEditing({} as Row);
  }

  function openEditForm(row: Row) {
    setError("");
    setNotice("");
    setEditing(row);
  }

  return <section>
    <div className="page-heading"><div><p className="eyebrow">QUẢN LÝ NGHIỆP VỤ</p><h1>Vận hành xưởng</h1>
      <p className="muted">Dữ liệu được đọc và ghi qua API backend/PostgreSQL; ID liên kết tham chiếu từ danh sách nghiệp vụ.</p></div>
      {canCreate && <button className="primary" onClick={openCreateForm}><Plus size={16}/>{resource.path === "material-issues" ? "Xuất vật tư" : `Thêm ${resource.title.toLowerCase()}`}</button>}
    </div>
    {notice && <div className="notice success"><Check size={16}/>{notice}<button onClick={() => setNotice("")}><X size={15}/></button></div>}
    {error && <div className="notice error">{error}<button onClick={() => setError("")}><X size={15}/></button></div>}
    {showFinancialReport && report && <div className="stats-grid financial-stats">
      {[["Doanh thu phát hành", report.billed_amount], ["Đã thu", report.collected_amount],
        ["Còn phải thu", report.outstanding_amount], ["Chi phí", report.expense_total]].map(([label, amount]) =>
        <article className="stat-card" key={String(label)}><p>{label}</p><strong>{money.format(Number(amount))}</strong>
          <small>{report.invoice_count} hóa đơn · Thu ròng {money.format(report.net_collected)}</small></article>)}
    </div>}
    <div className="toolbar"><select value={selected} onChange={event => {setSelected(event.target.value); setEditing(null); setError(""); setNotice("");}}>
      {allowed.map(([key]) => <option key={key} value={key}>{titles[key]}</option>)}
    </select><button className="secondary" onClick={() => void load()} disabled={busy}><RefreshCw size={15}/>Tải lại</button>
      <span className="toolbar-note">{busy ? "Đang tải..." : `${rows.length} bản ghi`}</span></div>
    <div className="table-card operations-table"><table><thead><tr>{resource.columns.map(column => <th key={column}>{column.split("_").join(" ").toUpperCase()}</th>)}<th/></tr></thead>
      <tbody>{rows.map(row => <tr key={row.id}>{resource.columns.map(column => <td key={column}>{readable(row[column])}</td>)}
        <td className="row-actions">{canUpdate && !(resource.path === "invoices" && row.status !== "draft") && <button className="icon-btn" title="Sửa" onClick={() => openEditForm(row)}><Pencil size={15}/></button>}
          {canRemove && !(resource.path === "operations" && row.status !== "planned")
            && !(resource.path === "admin/users" && row.id === user.id)
            && <button className="icon-btn danger-text" title="Xóa" onClick={() => void remove(row)}><Trash2 size={15}/></button>}</td></tr>)}
        {!rows.length && <tr><td className="empty" colSpan={resource.columns.length + 1}>{busy ? "Đang tải dữ liệu..." : "Chưa có dữ liệu."}</td></tr>}</tbody>
    </table></div>
    {editing && <div className="modal-backdrop" onMouseDown={event => {if (event.target === event.currentTarget) setEditing(null);}}>
      <form className="modal" onSubmit={save}><div className="modal-heading"><h2>{resource.path === "material-issues" ? "Xuất vật tư theo BOM" : `${editing.id ? "Cập nhật" : "Thêm"} ${resource.title.toLowerCase()}`}</h2>
        <button className="icon-btn" type="button" onClick={() => setEditing(null)}><X size={18}/></button></div>
        <div className="form-grid">{(resource.path === "admin/users" && editing.id
          ? resource.fields.filter(field => ["role", "is_active"].includes(field.key))
          : resource.fields.filter(field => !(resource.path === "admin/users" && field.key === "is_active"))).map(field => <label key={field.key} className={field.type === "textarea" ? "span-two" : ""}>
          {field.label}{field.type === "textarea" ? <textarea name={field.key} placeholder={field.placeholder} defaultValue={String(editing[field.key] ?? "")}/>
            : field.type === "checkbox" ? <input name={field.key} type="checkbox" defaultChecked={editing[field.key] == null ? true : Boolean(editing[field.key])}/>
            : field.type === "select" ? <select name={field.key} required defaultValue={String(
              editing[field.key] ?? field.defaultValue ?? "",
            )}><option value="">Chọn</option>
              {field.key === "order_id" && resource.path === "invoices" && editing.id
                && !invoiceOrderOptions.some(option => option.value === String(editing.order_id))
                && <option value={String(editing.order_id)}>{`Đơn #${editing.order_id} (đang gắn với hóa đơn)`}</option>}
              {field.key === "order_id" && resource.path === "invoices"
                ? invoiceOrderOptions.map(option => <option key={option.value} value={option.value}>{option.label}</option>)
                : field.options?.map(option => <option key={option} value={option}>{option}</option>)}</select>
            : <input name={field.key} type={field.type ?? "text"} required={!field.optional || (resource.path === "admin/users" && field.key === "password" && !editing.id)}
              step={field.type === "number" ? "any" : undefined}
              placeholder={field.placeholder}
              defaultValue={field.type === "datetime-local" && editing[field.key]
                ? new Date(String(editing[field.key])).toISOString().slice(0, 16)
              : field.type === "time" && editing[field.key]
                ? String(editing[field.key]).slice(0, 5)
            : String(editing[field.key] ?? field.defaultValue ?? "")}/>}
        </label>)}</div>
        <div className="modal-actions"><button className="secondary" type="button" onClick={() => setEditing(null)}>Hủy</button>
          <button className="primary" disabled={busy}>{busy ? "Đang xử lý..." : resource.path === "material-issues" ? "Kiểm tra và xuất kho" : "Lưu dữ liệu"}</button></div>
      </form>
    </div>}
  </section>;
}
