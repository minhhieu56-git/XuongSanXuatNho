import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Check, Pencil, Plus, RefreshCw, Trash2, X } from "lucide-react";
import { ApiError, request, type User } from "./api";

type Field = {
  key: string;
  label: string;
  type?: "number" | "date" | "time" | "datetime-local" | "textarea" | "checkbox" | "select" | "password";
  optional?: boolean;
  options?: string[];
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
    path: "admin/users", title: "Tài khoản", roles: ["admin"], createRoles: ["admin"], update: true, updateRoles: ["admin"],
    fields: [
      { key: "email", label: "Email" }, { key: "full_name", label: "Họ tên" },
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
      { key: "worker_code", label: "Mã công nhân" }, { key: "full_name", label: "Họ tên" },
      { key: "phone", label: "Điện thoại", optional: true }, { key: "skill", label: "Kỹ năng", optional: true },
      { key: "status", label: "Trạng thái", type: "select", options: ["active", "inactive"] },
      { key: "user_id", label: "ID tài khoản (nếu có)", type: "number", optional: true },
    ], columns: ["worker_code", "full_name", "phone", "skill", "status"],
  },
  customers: {
    path: "customers", title: "Khách hàng", roles: financeStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "customer_code", label: "Mã khách hàng" }, { key: "full_name", label: "Tên khách hàng" },
      { key: "phone", label: "Điện thoại", optional: true }, { key: "email", label: "Email", optional: true },
      { key: "shipping_address", label: "Địa chỉ", type: "textarea", optional: true },
      { key: "user_id", label: "ID tài khoản (nếu có)", type: "number", optional: true },
    ], columns: ["customer_code", "full_name", "phone", "email"],
  },
  "production-lines": {
    path: "production-lines", title: "Dây chuyền", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "line_code", label: "Mã dây chuyền" }, { key: "name", label: "Tên dây chuyền" },
      { key: "location", label: "Vị trí", optional: true }, { key: "is_active", label: "Đang hoạt động", type: "checkbox" },
    ], columns: ["line_code", "name", "location", "is_active"],
  },
  machines: {
    path: "machines", title: "Máy móc", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "machine_code", label: "Mã máy" }, { key: "name", label: "Tên máy" },
      { key: "line_id", label: "ID dây chuyền", type: "number", optional: true },
      { key: "status", label: "Trạng thái", type: "select", options: ["available", "operating", "maintenance", "broken"] },
      { key: "technical_notes", label: "Ghi chú kỹ thuật", type: "textarea", optional: true },
    ], columns: ["machine_code", "name", "line_id", "status"],
  },
  shifts: {
    path: "shifts", title: "Ca làm việc", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "name", label: "Tên ca" }, { key: "start_time", label: "Bắt đầu", type: "time" },
      { key: "end_time", label: "Kết thúc", type: "time" }, { key: "is_active", label: "Đang hoạt động", type: "checkbox" },
    ], columns: ["name", "start_time", "end_time", "is_active"],
  },
  schedules: {
    path: "schedules", title: "Lịch phân công", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "order_id", label: "ID đơn hàng", type: "number" }, { key: "worker_id", label: "ID công nhân", type: "number" },
      { key: "machine_id", label: "ID máy", type: "number" }, { key: "line_id", label: "ID dây chuyền", type: "number", optional: true },
      { key: "shift_id", label: "ID ca", type: "number", optional: true },
      { key: "starts_at", label: "Bắt đầu", type: "datetime-local" }, { key: "ends_at", label: "Kết thúc", type: "datetime-local" },
      { key: "status", label: "Trạng thái", type: "select", options: ["scheduled", "in_progress", "completed", "cancelled"] },
      { key: "notes", label: "Ghi chú", type: "textarea", optional: true },
    ], columns: ["order_id", "worker_id", "machine_id", "starts_at", "ends_at", "status"],
  },
  bom: {
    path: "bom", title: "Định mức BOM", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "product_name", label: "Sản phẩm" }, { key: "material_id", label: "ID nguyên liệu", type: "number" },
      { key: "quantity_per_unit", label: "Định mức / sản phẩm", type: "number" }, { key: "notes", label: "Ghi chú", type: "textarea", optional: true },
    ], columns: ["product_name", "material", "quantity_per_unit", "notes"],
  },
  operations: {
    path: "operations", title: "Công đoạn", roles: productionStaff, createRoles: managers, update: true, updateRoles: managers, remove: true, removeRoles: managers,
    fields: [
      { key: "order_id", label: "ID đơn hàng", type: "number" }, { key: "stage_name", label: "Tên công đoạn" },
      { key: "sequence", label: "Thứ tự", type: "number" },
      { key: "status", label: "Trạng thái", type: "select", options: ["planned", "in_progress", "completed", "blocked"] },
      { key: "completed_quantity", label: "Sản lượng đạt", type: "number" }, { key: "rejected_quantity", label: "Sản lượng lỗi", type: "number" },
      { key: "instructions", label: "Hướng dẫn", type: "textarea", optional: true },
    ], columns: ["order_id", "sequence", "stage_name", "status", "completed_quantity", "rejected_quantity"],
  },
  "production-logs": {
    path: "production-logs", title: "Nhật ký sản xuất", roles: productionStaff, createRoles: productionStaff,
    fields: [
      { key: "order_id", label: "ID đơn hàng", type: "number" }, { key: "operation_id", label: "ID công đoạn", type: "number", optional: true },
      { key: "worker_id", label: "ID công nhân", type: "number", optional: true }, { key: "machine_id", label: "ID máy", type: "number", optional: true },
      { key: "shift_id", label: "ID ca", type: "number", optional: true },
      { key: "good_quantity", label: "Sản phẩm đạt", type: "number" }, { key: "rejected_quantity", label: "Sản phẩm lỗi", type: "number" },
      { key: "incident_type", label: "Loại sự cố", optional: true }, { key: "notes", label: "Ghi chú", type: "textarea", optional: true },
    ], columns: ["order_id", "operation_id", "good_quantity", "rejected_quantity", "incident_type", "logged_at"],
  },
  defects: {
    path: "defects", title: "Lỗi chất lượng", roles: productionStaff, createRoles: productionStaff, update: true, updateRoles: managers,
    fields: [
      { key: "order_id", label: "ID đơn hàng", type: "number" }, { key: "operation_id", label: "ID công đoạn", type: "number", optional: true },
      { key: "quantity", label: "Số lượng lỗi", type: "number" }, { key: "defect_type", label: "Loại lỗi" },
      { key: "description", label: "Mô tả", type: "textarea", optional: true }, { key: "resolution", label: "Hướng xử lý", type: "textarea", optional: true },
    ], columns: ["order_id", "quantity", "defect_type", "description", "reported_at"],
  },
  invoices: {
    path: "invoices", title: "Hóa đơn", roles: [...financeStaff, "customer"], createRoles: financeStaff, update: true, updateRoles: financeStaff,
    fields: [
      { key: "invoice_code", label: "Mã hóa đơn" }, { key: "order_id", label: "ID đơn hàng", type: "number" },
      { key: "service_unit_price", label: "Đơn giá", type: "number" }, { key: "discount_amount", label: "Chiết khấu", type: "number" },
      { key: "status", label: "Trạng thái", type: "select", options: ["draft", "issued"] },
    ], columns: ["invoice_code", "order_id", "total_amount", "amount_paid", "status"],
  },
  payments: {
    path: "payments", title: "Thanh toán", roles: financeStaff,
    fields: [
      { key: "invoice_id", label: "ID hóa đơn", type: "number" }, { key: "amount", label: "Số tiền", type: "number" },
      { key: "method", label: "Phương thức", type: "select", options: ["cash", "bank_transfer"] },
      { key: "reference", label: "Mã tham chiếu", optional: true },
    ], columns: ["invoice_id", "amount", "method", "reference", "received_at"],
  },
  expenses: {
    path: "expenses", title: "Chi phí", roles: financeStaff, createRoles: financeStaff, update: true, updateRoles: financeStaff, remove: true, removeRoles: financeStaff,
    fields: [
      { key: "description", label: "Nội dung" }, { key: "category", label: "Danh mục" },
      { key: "amount", label: "Số tiền", type: "number" }, { key: "order_id", label: "ID đơn hàng", type: "number", optional: true },
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
    const formFields = resource.path === "admin/users" && editing?.id
      ? resource.fields.filter(field => ["role", "is_active"].includes(field.key))
      : resource.path === "admin/users"
        ? resource.fields.filter(field => field.key !== "is_active")
        : resource.fields;
    for (const field of formFields) {
      const raw = form.get(field.key);
      if (field.type === "checkbox") body[field.key] = raw === "on";
      else if (raw === "" || raw == null) body[field.key] = field.optional ? null : "";
      else if (field.type === "number") body[field.key] = Number(raw);
      else if (field.type === "datetime-local") body[field.key] = new Date(String(raw)).toISOString();
      else body[field.key] = String(raw);
    }
    setBusy(true); setError(""); setNotice("");
    try {
      await request(`/${resource.path}${editing ? `/${editing.id}` : ""}`, token, {
        method: editing ? "PUT" : "POST", body: JSON.stringify(body),
      });
      setEditing(null); setNotice("Đã lưu dữ liệu."); await load();
    } catch (issue) {
      setError(issue instanceof ApiError ? issue.message : issue instanceof Error ? issue.message : "Không lưu được dữ liệu.");
    } finally { setBusy(false); }
  }

  async function remove(row: Row) {
    if (!canRemove || !window.confirm(`Xóa bản ghi #${row.id}?`)) return;
    try {
      await request(`/${resource.path}/${row.id}`, token, { method: "DELETE" });
      setNotice("Đã xóa bản ghi."); await load();
    } catch (issue) { setError(issue instanceof Error ? issue.message : "Không xóa được dữ liệu."); }
  }

  return <section>
    <div className="page-heading"><div><p className="eyebrow">QUẢN LÝ NGHIỆP VỤ</p><h1>Vận hành xưởng</h1>
      <p className="muted">Dữ liệu được đọc và ghi qua API backend/PostgreSQL; ID liên kết tham chiếu từ danh sách nghiệp vụ.</p></div>
      {canCreate && <button className="primary" onClick={() => setEditing({} as Row)}><Plus size={16}/>Thêm {resource.title.toLowerCase()}</button>}
    </div>
    {notice && <div className="notice success"><Check size={16}/>{notice}<button onClick={() => setNotice("")}><X size={15}/></button></div>}
    {error && <div className="notice error">{error}<button onClick={() => setError("")}><X size={15}/></button></div>}
    {showFinancialReport && report && <div className="stats-grid financial-stats">
      {[["Doanh thu phát hành", report.billed_amount], ["Đã thu", report.collected_amount],
        ["Còn phải thu", report.outstanding_amount], ["Chi phí", report.expense_total]].map(([label, amount]) =>
        <article className="stat-card" key={String(label)}><p>{label}</p><strong>{money.format(Number(amount))}</strong>
          <small>{report.invoice_count} hóa đơn · Thu ròng {money.format(report.net_collected)}</small></article>)}
    </div>}
    <div className="toolbar"><select value={selected} onChange={event => {setSelected(event.target.value); setEditing(null);}}>
      {allowed.map(([key]) => <option key={key} value={key}>{titles[key]}</option>)}
    </select><button className="secondary" onClick={() => void load()} disabled={busy}><RefreshCw size={15}/>Tải lại</button>
      <span className="toolbar-note">{busy ? "Đang tải..." : `${rows.length} bản ghi`}</span></div>
    <div className="table-card operations-table"><table><thead><tr>{resource.columns.map(column => <th key={column}>{column.split("_").join(" ").toUpperCase()}</th>)}<th/></tr></thead>
      <tbody>{rows.map(row => <tr key={row.id}>{resource.columns.map(column => <td key={column}>{readable(row[column])}</td>)}
        <td className="row-actions">{canUpdate && !(resource.path === "invoices" && row.status !== "draft") && <button className="icon-btn" title="Sửa" onClick={() => setEditing(row)}><Pencil size={15}/></button>}
          {canRemove && !(resource.path === "operations" && row.status !== "planned") && <button className="icon-btn danger-text" title="Xóa" onClick={() => void remove(row)}><Trash2 size={15}/></button>}</td></tr>)}
        {!rows.length && <tr><td className="empty" colSpan={resource.columns.length + 1}>{busy ? "Đang tải dữ liệu..." : "Chưa có dữ liệu."}</td></tr>}</tbody>
    </table></div>
    {editing && <div className="modal-backdrop" onMouseDown={event => {if (event.target === event.currentTarget) setEditing(null);}}>
      <form className="modal" onSubmit={save}><div className="modal-heading"><h2>{editing.id ? "Cập nhật" : "Thêm"} {resource.title.toLowerCase()}</h2>
        <button className="icon-btn" type="button" onClick={() => setEditing(null)}><X size={18}/></button></div>
        <div className="form-grid">{(resource.path === "admin/users" && editing.id
          ? resource.fields.filter(field => ["role", "is_active"].includes(field.key))
          : resource.fields.filter(field => !(resource.path === "admin/users" && field.key === "is_active"))).map(field => <label key={field.key} className={field.type === "textarea" ? "span-two" : ""}>
          {field.label}{field.type === "textarea" ? <textarea name={field.key} defaultValue={String(editing[field.key] ?? "")}/>
            : field.type === "checkbox" ? <input name={field.key} type="checkbox" defaultChecked={editing[field.key] == null ? true : Boolean(editing[field.key])}/>
            : field.type === "select" ? <select name={field.key} required defaultValue={String(editing[field.key] ?? "")}><option value="">Chọn</option>
              {field.options?.map(option => <option key={option} value={option}>{option}</option>)}</select>
            : <input name={field.key} type={field.type ?? "text"} required={!field.optional || (resource.path === "admin/users" && field.key === "password" && !editing.id)}
              step={field.type === "number" ? "any" : undefined}
              defaultValue={field.type === "datetime-local" && editing[field.key]
                ? new Date(String(editing[field.key])).toISOString().slice(0, 16)
              : field.type === "time" && editing[field.key]
                ? String(editing[field.key]).slice(0, 5)
              : String(editing[field.key] ?? "")}/>}
        </label>)}</div>
        <p className="muted">Các trường ID liên kết lấy từ dữ liệu nghiệp vụ tương ứng. Máy chủ sẽ kiểm tra quan hệ và quyền.</p>
        <div className="modal-actions"><button className="secondary" type="button" onClick={() => setEditing(null)}>Hủy</button>
          <button className="primary" disabled={busy}>{busy ? "Đang lưu..." : "Lưu dữ liệu"}</button></div>
      </form>
    </div>}
  </section>;
}
