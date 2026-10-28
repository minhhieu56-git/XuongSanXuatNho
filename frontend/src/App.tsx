import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  Activity, Boxes, BrainCircuit, Check, ChevronDown, ClipboardList, LayoutDashboard, Pencil,
  LogOut, Plus, Search, Sparkles, Trash2, TriangleAlert, X,
} from "lucide-react";
import { ApiError, login, request, type Dashboard, type InventoryItem, type Order, type User } from "./api";

type Page = "dashboard" | "orders" | "inventory" | "ai";
type InventoryDraft = Omit<InventoryItem, "id" | "updated_at">;
type OrderDraft = Pick<Order, "order_code" | "product_name" | "quantity" | "due_date" | "status" | "notes" | "material_id">;

const currency = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 });
const statusNames: Record<string, string> = { planned: "Đã lên kế hoạch", in_progress: "Đang sản xuất", completed: "Hoàn thành", cancelled: "Đã hủy" };
const errorText = (error: unknown) => error instanceof Error ? error.message : "Đã xảy ra lỗi không xác định.";

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("workshop_token") ?? "");
  const [user, setUser] = useState<User | null>(null);
  const [page, setPage] = useState<Page>("dashboard");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [showInventoryForm, setShowInventoryForm] = useState(false);
  const [editingOrder, setEditingOrder] = useState<Order | null>(null);
  const [editingInventory, setEditingInventory] = useState<InventoryItem | null>(null);
  const [aiQuestion, setAiQuestion] = useState("Mặt hàng nào đang dưới mức tồn tối thiểu và tôi nên ưu tiên xử lý đơn hàng nào?");
  const [aiAnswer, setAiAnswer] = useState("");
  const [aiProvider, setAiProvider] = useState<"gemini" | "local">("local");
  const [loginEmail, setLoginEmail] = useState("admin@example.com");
  const [loginPassword, setLoginPassword] = useState("");

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      const [me, dash, stock, aiStatus] = await Promise.all([
        request<User>("/auth/me", token),
        request<Dashboard>("/dashboard", token),
        request<InventoryItem[]>("/inventory", token),
        request<{provider: "gemini" | "local"}>("/ai/status", token),
      ]);
      setUser(me);
      setDashboard(dash);
      setInventory(stock);
      setAiProvider(aiStatus.provider);
      const query = new URLSearchParams();
      if (search.trim()) query.set("search", search.trim());
      if (page === "orders" && statusFilter) query.set("order_status", statusFilter);
      const list = await request<Order[]>(`/orders${query.size ? `?${query}` : ""}`, token);
      setOrders(list);
      setError("");
    } catch (issue) {
      if (issue instanceof ApiError && issue.status === 401) {
        localStorage.removeItem("workshop_token");
        setToken("");
        setUser(null);
      } else setError(errorText(issue));
    }
  }, [token, search, statusFilter, page]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      const result = await login(loginEmail, loginPassword);
      localStorage.setItem("workshop_token", result.access_token);
      setToken(result.access_token);
      setUser(result.user);
    } catch (issue) { setError(errorText(issue)); }
    finally { setBusy(false); }
  }

  async function saveOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const material = String(form.get("material_id") ?? "");
    const payload: OrderDraft = {
      order_code: String(form.get("order_code")), product_name: String(form.get("product_name")),
      quantity: Number(form.get("quantity")), due_date: form.get("due_date") ? new Date(String(form.get("due_date"))).toISOString() : null,
      status: String(form.get("status")), notes: String(form.get("notes")) || null,
      material_id: material ? Number(material) : null,
    };
    await mutate(editingOrder ? `/orders/${editingOrder.id}` : "/orders", editingOrder ? "PUT" : "POST", payload, setShowOrderForm);
    setEditingOrder(null);
  }

  async function saveInventory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload: InventoryDraft = {
      sku: String(form.get("sku")), name: String(form.get("name")), unit: String(form.get("unit")),
      quantity: Number(form.get("quantity")), minimum_quantity: Number(form.get("minimum_quantity")),
      unit_cost: Number(form.get("unit_cost")),
    };
    await mutate(editingInventory ? `/inventory/${editingInventory.id}` : "/inventory", editingInventory ? "PUT" : "POST", payload, setShowInventoryForm);
    setEditingInventory(null);
  }

  async function mutate(path: string, method: string, body: unknown, close: (value: boolean) => void) {
    setBusy(true); setError(""); setMessage("");
    try {
      await request(path, token, { method, body: JSON.stringify(body) });
      close(false); setMessage("Đã lưu dữ liệu."); await refresh();
    } catch (issue) { setError(errorText(issue)); }
    finally { setBusy(false); }
  }

  async function deleteRecord(path: string) {
    if (!window.confirm("Bạn chắc chắn muốn xóa bản ghi này?")) return;
    try { await request(path, token, { method: "DELETE" }); setMessage("Đã xóa bản ghi."); await refresh(); }
    catch (issue) { setError(errorText(issue)); }
  }

  async function runAI(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setAiAnswer("");
    try {
      const result = await request<{answer: string; model: string; provider: string; data_scope: string}>("/ai/analysis", token, {
        method: "POST", body: JSON.stringify({ question: aiQuestion }),
      });
      const source = result.provider === "gemini"
        ? `Gemini: ${result.model}`
        : "Phân tích quy tắc nội bộ (chưa dùng Gemini)";
      setAiAnswer(`${result.answer}\n\nNguồn dữ liệu: ${result.data_scope} · ${source}`);
    } catch (issue) { setError(errorText(issue)); }
    finally { setBusy(false); }
  }

  function logout() { localStorage.removeItem("workshop_token"); setToken(""); setUser(null); setDashboard(null); }
  const canManage = user?.role === "admin" || user?.role === "manager";

  if (!token) return <main className="login-page">
    <form className="login-card" onSubmit={handleLogin}>
      <div className="brand-mark"><Boxes size={25} /></div>
      <p className="eyebrow">WORKSHOP OPERATIONS</p><h1>Quản lý xưởng<br />thông minh hơn.</h1>
      <p className="muted">Đăng nhập để theo dõi sản xuất và tồn kho.</p>
      <label>Email<input type="email" required value={loginEmail} onChange={e => setLoginEmail(e.target.value)} /></label>
      <label>Mật khẩu<input type="password" required minLength={8} value={loginPassword} onChange={e => setLoginPassword(e.target.value)} /></label>
      {error && <div className="notice error">{error}</div>}
      <button className="primary full" disabled={busy}>{busy ? "Đang đăng nhập..." : "Đăng nhập"}</button>
      <p className="hint">Demo: admin@example.com / ChangeMe123! (sau khi nạp dữ liệu mẫu)</p>
    </form>
  </main>;

  const nav: {id: Page; label: string; icon: typeof LayoutDashboard}[] = [
    {id: "dashboard", label: "Tổng quan", icon: LayoutDashboard},
    {id: "orders", label: "Đơn sản xuất", icon: ClipboardList},
    {id: "inventory", label: "Kho nguyên liệu", icon: Boxes},
    {id: "ai", label: "Phân tích AI", icon: BrainCircuit},
  ];

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Boxes size={22} /></div><div><b>Workshop</b><small>AI Operations</small></div></div>
      <div className="side-label">KHÔNG GIAN LÀM VIỆC</div>
      <nav>{nav.map(item => <button key={item.id} className={`nav-item ${page === item.id ? "active" : ""}`} onClick={() => setPage(item.id)}><item.icon size={18}/>{item.label}</button>)}</nav>
      <div className="sidebar-bottom"><div className="user-avatar">{user?.full_name.slice(0, 1)}</div><div className="user-info"><b>{user?.full_name}</b><small>{user?.role}</small></div><button className="icon-btn" title="Đăng xuất" onClick={logout}><LogOut size={17}/></button></div>
    </aside>
    <main className="main-area">
      <header className="topbar"><div className="breadcrumb">Xưởng sản xuất <span>/</span> {nav.find(item => item.id === page)?.label}</div><div className="live"><i/> Hệ thống hoạt động</div></header>
      <section className="content">
        {error && <div className="notice error"><TriangleAlert size={17}/>{error}<button onClick={() => setError("")}><X size={16}/></button></div>}
        {message && <div className="notice success"><Check size={17}/>{message}<button onClick={() => setMessage("")}><X size={16}/></button></div>}
        {page === "dashboard" && <DashboardPage dashboard={dashboard} orders={orders} setPage={setPage}/>}
        {page === "orders" && <section>
          <div className="page-heading"><div><p className="eyebrow">SẢN XUẤT</p><h1>Đơn sản xuất</h1><p className="muted">Quản lý tiến độ và kế hoạch đơn hàng.</p></div>{canManage && <button className="primary" onClick={() => {setEditingOrder(null); setShowOrderForm(true);}}><Plus size={17}/> Tạo đơn hàng</button>}</div>
          <div className="toolbar"><div className="searchbox"><Search size={17}/><input placeholder="Tìm mã đơn hoặc sản phẩm..." value={search} onChange={e => setSearch(e.target.value)}/></div><select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option value="">Tất cả trạng thái</option>{Object.entries(statusNames).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></div>
          <div className="table-card"><table><thead><tr><th>MÃ ĐƠN</th><th>SẢN PHẨM</th><th>SỐ LƯỢNG</th><th>NGUYÊN LIỆU</th><th>HẠN HOÀN THÀNH</th><th>TRẠNG THÁI</th>{canManage && <th/>}</tr></thead><tbody>{orders.map(order => <tr key={order.id}><td className="strong">{order.order_code}</td><td>{order.product_name}</td><td>{order.quantity.toLocaleString("vi-VN")}</td><td>{order.material?.name ?? "—"}</td><td>{order.due_date ? new Date(order.due_date).toLocaleDateString("vi-VN") : "—"}</td><td><span className={`status ${order.status}`}>{statusNames[order.status] ?? order.status}</span></td>{canManage && <td className="row-actions"><button className="icon-btn" title="Sửa đơn" onClick={() => {setEditingOrder(order); setShowOrderForm(true);}}><Pencil size={15}/></button><button className="icon-btn danger-text" title="Xóa" onClick={() => void deleteRecord(`/orders/${order.id}`)}><Trash2 size={16}/></button></td>}</tr>)}{orders.length === 0 && <tr><td colSpan={7} className="empty">Không tìm thấy đơn hàng phù hợp.</td></tr>}</tbody></table></div>
        </section>}
        {page === "inventory" && <section>
          <div className="page-heading"><div><p className="eyebrow">VẬT TƯ</p><h1>Kho nguyên liệu</h1><p className="muted">Theo dõi số lượng và cảnh báo tồn kho tối thiểu.</p></div>{canManage && <button className="primary" onClick={() => {setEditingInventory(null); setShowInventoryForm(true);}}><Plus size={17}/> Thêm nguyên liệu</button>}</div>
          <div className="toolbar"><div className="searchbox"><Search size={17}/><input placeholder="Tìm theo SKU hoặc tên..." value={search} onChange={e => setSearch(e.target.value)}/></div><span className="toolbar-note">{inventory.length} mặt hàng</span></div>
          <div className="inventory-grid">{inventory.filter(item => `${item.name} ${item.sku}`.toLowerCase().includes(search.toLowerCase())).map(item => {
            const low = item.quantity <= item.minimum_quantity;
            return <article className="stock-card" key={item.id}><div className="stock-top"><div className="stock-icon"><Boxes size={19}/></div><span className={`stock-flag ${low ? "low" : ""}`}>{low ? "Sắp hết" : "Ổn định"}</span></div><p className="sku">{item.sku}</p><h3>{item.name}</h3><div className="stock-number">{item.quantity.toLocaleString("vi-VN")} <small>{item.unit}</small></div><div className="stock-bottom"><span>Tối thiểu: {item.minimum_quantity} {item.unit}</span><span>{currency.format(item.unit_cost)}/{item.unit}</span></div>{canManage && <div className="stock-actions"><button className="icon-btn" title="Sửa nguyên liệu" onClick={() => {setEditingInventory(item); setShowInventoryForm(true);}}><Pencil size={15}/></button><button className="icon-btn danger-text" title="Xóa" onClick={() => void deleteRecord(`/inventory/${item.id}`)}><Trash2 size={15}/></button></div>}</article>;
          })}</div>
        </section>}
        {page === "ai" && <section>
          <div className="page-heading"><div><p className="eyebrow">WORKSHOP OPERATIONS ASSISTANT</p><h1>Phân tích AI</h1><p className="muted">Hỏi về đơn hàng và tồn kho. Kết quả phân tích chỉ mang tính tham khảo, không tự sửa giao dịch.</p></div><div className="ai-orb"><Sparkles size={22}/></div></div>
          {aiProvider === "local" && <div className="notice ai-notice"><Sparkles size={17}/>Chưa cấu hình Gemini: hệ thống vẫn phân tích tồn kho và đơn hàng bằng quy tắc nội bộ. Thêm GEMINI_API_KEY vào tệp .env ở thư mục gốc và khởi động lại backend để bật mô hình Gemini.</div>}
          <div className="ai-layout"><div className="ai-card"><div className="ai-card-title"><div className="mini-icon"><BrainCircuit size={18}/></div><div><b>Trợ lý vận hành</b><small>Dữ liệu đơn hàng & tồn kho hiện tại</small></div><span className="live"><i/> Sẵn sàng</span></div>
            <form onSubmit={runAI}><label htmlFor="question">Câu hỏi của bạn</label><textarea id="question" minLength={5} maxLength={1000} value={aiQuestion} onChange={e => setAiQuestion(e.target.value)} required/><div className="prompt-suggestions"><span>Gợi ý:</span><button type="button" onClick={() => setAiQuestion("Nguyên liệu nào đang dưới mức tồn tối thiểu?")}>Kiểm tra tồn kho thấp</button><button type="button" onClick={() => setAiQuestion("Tóm tắt các đơn hàng cần ưu tiên theo hạn hoàn thành.")}>Ưu tiên đơn hàng</button></div><button className="primary" disabled={busy}><Sparkles size={16}/>{busy ? "Đang phân tích..." : "Phân tích dữ liệu"}</button></form>
            {aiAnswer && <div className="ai-result"><h3><Activity size={17}/> Kết quả phân tích</h3><div className="answer-text">{aiAnswer}</div><p className="ai-disclaimer">Đề xuất do AI tạo có thể không chính xác. Hãy kiểm chứng trước khi quyết định.</p></div>}
            {!aiAnswer && <div className="ai-placeholder"><Sparkles size={22}/><p>Kết quả phân tích sẽ hiển thị tại đây.</p></div>}</div>
            <aside className="ai-side"><h3>Phạm vi dữ liệu</h3><div><ClipboardList size={17}/><span>Đơn sản xuất</span><b>{dashboard?.order_count ?? 0}</b></div><div><Boxes size={17}/><span>Mặt hàng kho</span><b>{inventory.length}</b></div><div><TriangleAlert size={17}/><span>Tồn kho thấp</span><b>{dashboard?.low_stock_count ?? 0}</b></div><hr/><p>Kết quả sử dụng dữ liệu vận hành cần thiết của hệ thống. Khi chưa có API key, phân tích quy tắc được chạy nội bộ và không gửi dữ liệu ra ngoài.</p><small>Trợ lý không thực hiện thay đổi dữ liệu.</small></aside></div>
        </section>}
      </section>
    </main>
    {showOrderForm && <Modal title={editingOrder ? "Cập nhật đơn sản xuất" : "Tạo đơn sản xuất"} close={() => {setShowOrderForm(false); setEditingOrder(null);}} onSubmit={saveOrder} busy={busy}>
      <div className="form-grid"><label>Mã đơn<input name="order_code" required maxLength={40} placeholder="PX-2026-004" defaultValue={editingOrder?.order_code ?? ""}/></label><label>Tên sản phẩm<input name="product_name" required maxLength={160} defaultValue={editingOrder?.product_name ?? ""}/></label><label>Số lượng<input name="quantity" type="number" min="1" required defaultValue={editingOrder?.quantity ?? ""}/></label><label>Hạn hoàn thành<input name="due_date" type="date" defaultValue={editingOrder?.due_date ? new Date(editingOrder.due_date).toISOString().slice(0, 10) : ""}/></label><label>Trạng thái<select name="status" defaultValue={editingOrder?.status ?? "planned"}>{Object.entries(statusNames).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label><label>Nguyên liệu liên quan<select name="material_id" defaultValue={editingOrder?.material_id ?? ""}><option value="">Không chọn</option>{inventory.map(item => <option value={item.id} key={item.id}>{item.name} ({item.sku})</option>)}</select></label><label className="span-two">Ghi chú<textarea name="notes" maxLength={4000} defaultValue={editingOrder?.notes ?? ""}/></label></div>
    </Modal>}
    {showInventoryForm && <Modal title={editingInventory ? "Cập nhật nguyên liệu" : "Thêm nguyên liệu"} close={() => {setShowInventoryForm(false); setEditingInventory(null);}} onSubmit={saveInventory} busy={busy}>
      <div className="form-grid"><label>SKU<input name="sku" required maxLength={40} defaultValue={editingInventory?.sku ?? ""}/></label><label>Tên nguyên liệu<input name="name" required maxLength={160} defaultValue={editingInventory?.name ?? ""}/></label><label>Đơn vị<input name="unit" required maxLength={30} placeholder="kg, cái, lít" defaultValue={editingInventory?.unit ?? ""}/></label><label>Số lượng hiện có<input name="quantity" type="number" step="0.01" min="0" required defaultValue={editingInventory?.quantity ?? ""}/></label><label>Mức tồn tối thiểu<input name="minimum_quantity" type="number" step="0.01" min="0" required defaultValue={editingInventory?.minimum_quantity ?? ""}/></label><label>Đơn giá (VND)<input name="unit_cost" type="number" step="0.01" min="0" required defaultValue={editingInventory?.unit_cost ?? ""}/></label></div>
    </Modal>}
  </div>;
}

function DashboardPage({dashboard, orders, setPage}: {dashboard: Dashboard | null; orders: Order[]; setPage: (page: Page) => void}) {
  const today = new Intl.DateTimeFormat("vi-VN", {weekday:"long", day:"numeric", month:"long"}).format(new Date());
  const stats = [
    {label:"Tổng đơn sản xuất", value:dashboard?.order_count ?? "—", icon:ClipboardList, note:"Tất cả trạng thái", color:"blue"},
    {label:"Đang thực hiện", value:dashboard?.active_order_count ?? "—", icon:Activity, note:"Đơn đang sản xuất", color:"orange"},
    {label:"Đơn hoàn thành", value:dashboard?.completed_order_count ?? "—", icon:Check, note:"Đã hoàn tất", color:"green"},
    {label:"Cảnh báo tồn kho", value:dashboard?.low_stock_count ?? "—", icon:TriangleAlert, note:"Dưới mức tối thiểu", color:"red"},
  ];
  return <section><div className="page-heading"><div><p className="eyebrow">{today.toLocaleUpperCase("vi-VN")}</p><h1>Tổng quan xưởng</h1><p className="muted">Theo dõi tình hình sản xuất và nguyên liệu hôm nay.</p></div><button className="secondary" onClick={() => setPage("ai")}><Sparkles size={16}/> Hỏi trợ lý AI</button></div>
    <div className="stats-grid">{stats.map(({label,value,icon:Icon,note,color})=><article className="stat-card" key={label}><div className={`stat-icon ${color}`}><Icon size={19}/></div><p>{label}</p><strong>{value}</strong><small>{note}</small></article>)}</div>
    <div className="dashboard-lower"><div className="table-card"><div className="card-heading"><div><h2>Đơn sản xuất gần đây</h2><p>Cập nhật danh sách đơn gần nhất</p></div><button className="text-btn" onClick={() => setPage("orders")}>Xem tất cả <ChevronDown size={15}/></button></div><table><thead><tr><th>MÃ ĐƠN</th><th>SẢN PHẨM</th><th>SỐ LƯỢNG</th><th>TRẠNG THÁI</th></tr></thead><tbody>{(dashboard?.recent_orders ?? orders.slice(0,5)).map(order=><tr key={order.id}><td className="strong">{order.order_code}</td><td>{order.product_name}</td><td>{order.quantity}</td><td><span className={`status ${order.status}`}>{statusNames[order.status] ?? order.status}</span></td></tr>)}{!dashboard?.recent_orders?.length && <tr><td colSpan={4} className="empty">Chưa có đơn hàng.</td></tr>}</tbody></table></div>
      <aside className="value-card"><div className="stock-icon"><Boxes size={19}/></div><p>Giá trị tồn kho</p><strong>{currency.format(Number(dashboard?.inventory_value ?? 0))}</strong><small>Tổng giá trị nguyên liệu hiện có</small><button className="secondary full" onClick={() => setPage("inventory")}>Xem kho nguyên liệu</button></aside></div>
  </section>;
}

function Modal({title,close,onSubmit,busy,children}: {title:string;close:()=>void;onSubmit:(event:FormEvent<HTMLFormElement>)=>void;busy:boolean;children:React.ReactNode}) {
  return <div className="modal-backdrop" onMouseDown={event => {if(event.target===event.currentTarget) close();}}><form className="modal" onSubmit={onSubmit}><div className="modal-heading"><h2>{title}</h2><button className="icon-btn" type="button" onClick={close}><X size={19}/></button></div>{children}<div className="modal-actions"><button className="secondary" type="button" onClick={close}>Hủy</button><button className="primary" disabled={busy}>{busy ? "Đang lưu..." : "Lưu dữ liệu"}</button></div></form></div>;
}
