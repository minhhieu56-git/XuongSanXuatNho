# Workshop AI — Quản lý xưởng sản xuất

Ứng dụng web quản lý sản xuất xưởng với React/TypeScript, FastAPI, SQLAlchemy, PostgreSQL 16 và Gemini API (tùy chọn cấu hình). Có đăng nhập JWT, phân quyền 5 vai trò, quản lý nguồn lực/lịch sản xuất, BOM, nhật ký/chất lượng, tài chính, báo cáo và các trợ lý AI theo nghiệp vụ.

## Yêu cầu môi trường

- Python 3.11 trở lên và PostgreSQL 16 đang chạy, có thể kết nối theo `DATABASE_URL`.
- Node.js 20 trở lên.
- Không cần và không sử dụng Docker Compose trong hướng dẫn chạy này.

## Cấu hình và chạy trên Windows

1. Tạo `.env` từ mẫu:

   ```powershell
   Copy-Item .env.example .env
   ```

   Cập nhật `DATABASE_URL`, `JWT_SECRET` bằng thông tin môi trường của bạn. Đặt `GEMINI_API_KEY` trong `.env` nếu muốn gọi Gemini. Không chia sẻ key, không đưa `.env` vào Git.

2. Cài backend, nâng cấp schema bổ sung an toàn và tạo dữ liệu demo:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m app.seed
   uvicorn app.main:app --reload --port 8001
   ```

   Schema được bổ sung theo hướng additive, không xóa dữ liệu hiện có. API docs: <http://localhost:8001/docs>; health check: <http://localhost:8001/health>.

3. Ở cửa sổ PowerShell khác:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Truy cập <http://localhost:5173>. Vite proxy chuyển `/api` tới backend cổng `8001`.

### Tài khoản demo

`python -m app.seed` tạo idempotent năm tài khoản `admin@example.com`, `manager@example.com`, `worker@example.com`, `accountant@example.com`, `customer@example.com`, mật khẩu demo `ChangeMe123!`. Hãy đổi mật khẩu hoặc thay tài khoản trước khi triển khai thật. Seed chỉ thêm dữ liệu mẫu còn thiếu, không ghi đè các bản ghi đã tồn tại.

## Phạm vi đang có

- **Admin:** quản lý tài khoản (tạo, đổi vai trò/trạng thái, reset mật khẩu, xóa tài khoản chưa bị dữ liệu nghiệp vụ sử dụng), audit log. Tài khoản đang đăng nhập không thể tự xóa; nếu tài khoản đã được tham chiếu thì cần vô hiệu hóa thay vì xóa.
- **Manager:** quản lý đơn, công nhân, khách hàng, máy, dây chuyền, ca, lịch; BOM, công đoạn, lỗi, hóa đơn/chi phí và AI.
- **Worker:** xem đơn được phân công, lịch cá nhân, BOM/quy trình; ghi nhật ký sản lượng/sự cố và lỗi chất lượng.
- **Accountant:** xem dữ liệu cần cho kế toán, lập hóa đơn/ghi thanh toán, quản lý chi phí, xem báo cáo tài chính.
- **Customer:** chỉ xem đơn/hóa đơn của hồ sơ liên kết, theo dõi tiến độ công đoạn, tạo yêu cầu sản xuất và chỉnh/hủy đơn còn ở trạng thái chờ.
- API backend là nguồn kiểm soát quyền; frontend chỉ ẩn thao tác không được phép, không thay thế RBAC server-side.
- Lịch chặn giao nhau trên cùng công nhân hoặc máy trong trạng thái đang hoạt động; PostgreSQL dùng advisory transaction lock để tuần tự hóa thao tác xếp lịch.
- Xuất vật tư theo BOM kiểm tra tồn kho trước khi ghi giao dịch, cập nhật tồn kho nguyên tử, lưu lịch sử xuất; thiếu bất kỳ vật tư nào thì toàn bộ lần xuất bị từ chối. Không cho sửa BOM, đổi số lượng/sản phẩm hoặc hủy/xóa đơn đã xuất vật tư.
- Tiến độ công đoạn được tính từ sản lượng đạt/lỗi lũy kế theo từng công đoạn; log không được vượt số lượng đơn. Công nhân chỉ được ghi log/sự cố cho đơn có lịch phân công.
- Hóa đơn tính thành tiền từ số lượng đơn hàng × đơn giá dịch vụ, áp chiết khấu, theo dõi thanh toán một phần/đầy đủ; báo cáo có lọc ngày.
- Audit log ghi nhận thay đổi chính của tài khoản, đơn hàng, kho và các module mới.

## AI và quyền riêng tư

- Gemini được gọi phía backend; API key không được gửi xuống React. Nếu chưa cấu hình key, phân tích kho/đơn, tóm tắt ca, bản nháp tiến độ và giải thích BOM có fallback nội bộ, được đánh dấu là phân tích nội bộ.
- Bốn luồng hiện có: phân tích đơn/kho, tóm tắt nhật ký ca, tạo bản nháp tiến độ (không tự gửi), giải thích BOM/công đoạn.
- Giá vốn không nằm trong context gửi Gemini; email, điện thoại, chuỗi số định danh 9–12 chữ số và một số trường tên/địa chỉ được gắn nhãn được che trước khi gọi. Context AI chỉ lấy dữ liệu tối thiểu cần thiết, có giới hạn số bản ghi và giới hạn kích thước.
- Bộ lọc prompt injection hiện là heuristic có test với một số câu tiếng Anh/tiếng Việt, không phải bộ phân loại toàn diện. Che tên/địa chỉ bằng regex không đảm bảo nhận diện mọi cách viết; **không gửi dữ liệu nhạy cảm hoặc dữ liệu thật chưa được kiểm soát**. Chưa có bằng chứng để tuyên bố masking 100% hoặc chặn jailbreak ≥95%.
- Mọi phản hồi AI có disclaimer. Kết quả chỉ tham khảo, nhân sự có thẩm quyền phải kiểm chứng; AI không tự tạo giao dịch.
- Cấu hình `GEMINI_MODEL` theo model mà API key của bạn được cấp quyền. Lỗi timeout, giới hạn tốc độ, model hoặc response rỗng được trả thành lỗi API có thông báo.

## Kiểm thử

```powershell
cd backend
python -m pytest -q

cd ..\frontend
npm run build
```

Kết quả xác minh gần nhất: **29 backend tests pass**, Python compile pass và React TypeScript/Vite production build pass. Test kiểm tra xuất vật tư theo BOM nguyên tử/không xuất lặp, tổng hợp tiến độ công đoạn, chặn vượt sản lượng, quyền theo phân công và lỗi hóa đơn trùng đơn. Test API dùng SQLite; bảng `material_issues` và ràng buộc được xác nhận trên PostgreSQL 16 local. Gemini request được kiểm thử bằng mock; không phải benchmark dịch vụ thật.

Chưa có bằng chứng đo ngưỡng CRUD `<1,5s`, Gemini `<5s`, tải đồng thời `50–100`, tỷ lệ chặn jailbreak `≥95%`, E2E trình duyệt/tablet, hoặc khôi phục backup. Không coi các mục tiêu định lượng trong báo cáo là đã đạt chỉ dựa trên unit/API tests.

## Cấu trúc

```text
backend/app/api/          REST routes
backend/app/core/         cấu hình, database, auth, schema migration
backend/app/models/       SQLAlchemy entities/relations
backend/app/prompts/      system/task prompts
backend/app/schemas/      request/response validation
backend/app/services/     Gemini và phân tích nội bộ
backend/tests/            API integration tests
frontend/src/             React UI và API client
docs/                     phân tích, yêu cầu và nhật ký bằng chứng AI
```

## Giới hạn và triển khai thật

- `upgrade_schema()` là migration bootstrap additive/idempotent cho thay đổi hiện có, chưa thay thế lịch sử migration có version như Alembic. Sao lưu database trước khi nâng cấp production.
- Chưa có flow duyệt đơn đầy đủ, tự động xuất kho khi chuyển trạng thái sản xuất (hiện quản đốc chủ động xuất theo BOM), hoàn trả vật tư đã xuất, kết nối gửi SMS/Zalo/email, bảo trì dự đoán, backup/restore tự động hoặc E2E/load test. Tiến độ phần trăm hiện là trung bình tỷ lệ hoàn tất của các công đoạn đã cấu hình; cần nghiệp vụ xác nhận đây là công thức phù hợp.
- JWT lưu ở localStorage để demo; cần đánh giá cookie `HttpOnly`/`Secure`/`SameSite`, CSP/XSS, thu hồi token và TLS khi triển khai internet-facing.
- Thay secrets mặc định, không dùng mật khẩu demo, bật TLS, cấu hình CORS tối thiểu và quản lý quyền DB theo nguyên tắc least privilege.

## Tài liệu

- [Phân tích và thiết kế](docs/ANALYSIS_DESIGN.md)
- [Nhật ký và kế hoạch kiểm chứng AI](docs/AI_EVIDENCE.md)
- [Yêu cầu trích xuất từ báo cáo và đối chiếu code](docs/REQUIREMENTS_FROM_REPORT.md)
