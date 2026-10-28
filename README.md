# Workshop AI — Quản lý xưởng sản xuất

MVP quản lý đơn sản xuất và nguyên vật liệu, có đăng nhập/phân quyền, dashboard và trợ lý phân tích Gemini. Stack: React + TypeScript + Vite, FastAPI + SQLAlchemy, PostgreSQL 16.

## Chạy thử trên Windows

Yêu cầu: Python 3.11+, Node.js 20+, Docker Desktop.

1. Tạo cấu hình môi trường:

   ```powershell
   Copy-Item .env.example .env
   ```

   Trước khi dùng ngoài máy cá nhân, thay `POSTGRES_PASSWORD` và `JWT_SECRET` bằng giá trị ngẫu nhiên đủ mạnh. Đặt `GEMINI_API_KEY` trong `.env` để bật trợ lý AI. Không đưa `.env` lên Git.

2. Khởi động PostgreSQL 16:

   ```powershell
   docker compose up -d db
   ```

3. Cài và khởi động backend:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m app.seed
   uvicorn app.main:app --reload --port 8001
   ```

   API docs: <http://localhost:8001/docs>, health check: <http://localhost:8001/health>.

4. Trong cửa sổ PowerShell khác, cài và khởi động frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Truy cập <http://localhost:5173>. Vite chuyển tiếp `/api` tới backend ở cổng 8001, tránh gọi nhầm dịch vụ khác trên cổng 8000. Các tài khoản demo `admin@example.com`, `manager@example.com`, `worker@example.com` dùng chung mật khẩu `ChangeMe123!`; hãy đổi hoặc xóa tài khoản demo trước khi triển khai thật.

### Phân tích AI

- Không có Gemini API key: chức năng vẫn phân tích nội bộ các mặt hàng dưới ngưỡng tồn và đơn chưa hoàn tất bằng quy tắc xác định. Kết quả ghi rõ đây không phải phản hồi Gemini.
- Muốn dùng mô hình Gemini: tạo API key riêng, thêm `GEMINI_API_KEY=<key-cua-ban>` vào `.env` ở thư mục gốc, rồi dừng và chạy lại backend. Model mặc định là `gemini-3.5-flash-lite`; có thể đổi bằng `GEMINI_MODEL` nếu model đó được cấp cho API key của bạn. Không chia sẻ API key trong chat hoặc đưa `.env` lên Git.

5. Chạy kiểm thử backend:

   ```powershell
   cd backend
   python -m pytest -q
   ```

   Kiểm tra frontend production build:

   ```powershell
   cd frontend
   npm run build
   ```

## Phạm vi MVP

- Đăng nhập bằng email/mật khẩu, JWT, vai trò `admin`, `manager`, `worker`; manager/admin được tạo, sửa, xóa đơn và vật tư. Worker chỉ đọc dữ liệu.
- CRUD đơn sản xuất và vật tư, tìm kiếm/lọc theo từ khóa/trạng thái, sắp xếp vật tư; kiểm tra khóa ngoại và mã/SKU trùng.
- Dashboard tổng đơn, đơn đang sản xuất/đã hoàn thành, cảnh báo tồn tối thiểu, giá trị kho và đơn gần đây.
- Gemini phân tích dữ liệu đơn và kho theo quyền đăng nhập; timeout/rate limit/phản hồi rỗng được báo lỗi. AI chỉ tư vấn, không được phép ghi dữ liệu.

## Cấu trúc

```text
backend/
  app/api/          API routes
  app/core/         cấu hình, database, bảo mật, dependency
  app/models/       entity và quan hệ SQLAlchemy
  app/prompts/      system prompt AI
  app/schemas/      request/response validation
  app/services/     tích hợp Gemini
  tests/            API tests
frontend/
  src/              giao diện React và API client
docker-compose.yml  PostgreSQL 16
docs/               phân tích, thiết kế và nhật ký AI
```

## Lưu ý triển khai

- Cấu hình trong `.env` là bắt buộc cho môi trường triển khai; không dùng JWT secret mặc định.
- Bản MVP tạo bảng bằng `create_all`; dự án triển khai thật cần bổ sung Alembic migrations, HTTPS, quản lý vòng đời token/session, quy trình đổi mật khẩu và tài khoản người dùng do admin quản lý.
- JWT được lưu phía trình duyệt để thuận tiện demo. Với hệ thống internet-facing nên đánh giá lại mô hình token, CSP/XSS, cookie `HttpOnly`/`Secure`/`SameSite`, CSRF và chính sách lưu giữ dữ liệu.
- Hiện chưa có workflow công đoạn/nhân công, định mức nguyên liệu để tự động trừ kho, khôi phục backup, logging/audit trail và kiểm thử end-to-end.
- `docker-compose.yml` chỉ khởi chạy PostgreSQL; backend/frontend được chạy riêng theo hướng dẫn trên.

## Tài liệu

- [Phân tích và thiết kế](docs/ANALYSIS_DESIGN.md)
- [Nhật ký và kế hoạch kiểm chứng AI](docs/AI_EVIDENCE.md)
