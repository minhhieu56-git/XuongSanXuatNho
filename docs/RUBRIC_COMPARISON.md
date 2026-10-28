# Đối chiếu 38 tiêu chí đánh giá

Đánh giá dựa trên code và tài liệu hiện có trong repository. **Đạt** nghĩa là có triển khai trong phạm vi MVP; **Một phần** nghĩa là đã có nền tảng nhưng còn thiếu phạm vi, dữ liệu kiểm chứng hoặc vận hành; **Chưa đạt** nghĩa là chưa có minh chứng/hiện vật cần thiết. Đặc biệt, API Gemini thật và PostgreSQL chưa chạy được xác nhận trong môi trường này: Docker không tải được image do kết nối registry bị chặn và chưa có `GEMINI_API_KEY`.

| # | Tiêu chí | Trạng thái | Hiện vật / phần còn thiếu |
|---:|---|---|---|
| 1 | Phân tích đúng bài toán quản lý | Đạt | Bối cảnh, actor, dữ liệu và quy trình MVP trong `ANALYSIS_DESIGN.md`. |
| 2 | Yêu cầu chức năng đầy đủ | Một phần | Có CRUD đơn/vật tư, lọc, dashboard, AI; chưa có công đoạn, nhân công, BOM, nhập/xuất kho và sản lượng thực tế. |
| 3 | Yêu cầu phi chức năng | Một phần | Nêu bảo mật, hiệu năng, khả dụng, backup và UX; backup, giám sát, phân trang và vận hành chưa triển khai. |
| 4 | Actor và use case | Đạt | Actor và sơ đồ use case Mermaid có trong tài liệu phân tích. |
| 5 | Thiết kế CSDL | Một phần | ERD, PK/FK/unique/check constraints có; schema hiện chỉ gồm users, vật tư và đơn, chưa có BOM/công đoạn/nhân công/lịch sử kho. |
| 6 | Kiến trúc hệ thống | Đạt | Mô tả React, FastAPI, SQLAlchemy, PostgreSQL, Gemini và luồng dữ liệu. |
| 7 | Vị trí ứng dụng AI | Đạt | Gemini phân tích snapshot đơn sản xuất và mức tồn nguyên liệu. |
| 8 | Prompt và luồng gọi AI | Đạt | System prompt tách file; user prompt, JSON context, text output, giới hạn và cảnh báo được mô tả. |
| 9 | Minh chứng AI phân tích/thiết kế | Một phần | Có mẫu nhật ký và quy trình kiểm chứng; chưa có prompt/response thực tế của nhóm. |
| 10 | Tài liệu phân tích thiết kế | Đạt | Tài liệu có cấu trúc, thiết kế và kế hoạch triển khai giai đoạn tiếp theo. |
| 11 | Cấu trúc dự án | Đạt | Tách backend, frontend, docs, config và tests. |
| 12 | Đăng nhập và phân quyền | Một phần | JWT, hash Argon2, vai trò và quyền ghi đã có; chưa có giao diện quản trị tài khoản, đổi/reset mật khẩu hay rate limit đăng nhập. |
| 13 | CRUD nghiệp vụ chính | Đạt | UI và API hỗ trợ tạo/xem/sửa/xóa đơn sản xuất và nguyên liệu. |
| 14 | Tìm kiếm, lọc, sắp xếp | Một phần | Tìm kiếm đơn/vật tư, lọc trạng thái đơn và tồn thấp qua API; chưa có phân trang và UI điều khiển đầy đủ cho sắp xếp/lọc kho. |
| 15 | Thống kê/báo cáo | Một phần | Dashboard có số liệu tổng quan và giá trị kho; chưa có báo cáo xuất file/biểu đồ theo thời gian. |
| 16 | Giao diện và thông báo | Đạt | Có màn hình đăng nhập, dashboard, danh sách, biểu mẫu, trạng thái tải, xác nhận xóa, báo lỗi/thành công và CSS responsive. |
| 17 | Kết nối CSDL và dữ liệu mẫu | Một phần | SQLAlchemy/PostgreSQL 16, seed idempotent và SQLite test có; PostgreSQL thật chưa xác minh vì không tải được Docker image. |
| 18 | Xử lý lỗi cơ bản | Một phần | Validate dữ liệu, 401/403/404/409 và lỗi Gemini; chưa có xử lý/quan sát lỗi DB toàn cục và audit log. |
| 19 | Minh chứng AI khi lập trình | Chưa đạt | Có mẫu nhật ký nhưng chưa có prompt/response hoặc review evidence thực tế. |
| 20 | Mã nguồn, README, chạy thử | Một phần | Có README, `.env.example`, seed và test; workspace chưa có Git history/commit và Compose mới chạy DB, chưa đóng gói app. |
| 21 | Tích hợp AI vào hệ thống | Một phần | Giao diện chạy phân tích quy tắc nội bộ khi chưa có key; luồng Gemini đã nối nhưng chưa chạy xác minh với tài khoản Gemini thật. |
| 22 | Kết nối API/model và bảo vệ key | Một phần | Gemini REST được gọi server-side, key ở biến môi trường; chưa xác minh request thật do thiếu key. |
| 23 | Prompt có hệ thống | Đạt | System prompt tách file, user prompt tạo từ câu hỏi và snapshot DB, có grounding/giới hạn. |
| 24 | Tối ưu prompt qua ít nhất 3 vòng | Chưa đạt | Tài liệu có kế hoạch 3 vòng, nhưng chưa chạy và ghi kết quả thực nghiệm. |
| 25 | AI dùng dữ liệu hệ thống, kiểm soát quyền | Một phần | Context được lấy từ DB và API đòi đăng nhập; phân quyền hiện chưa giới hạn từng tập dữ liệu theo vai trò. |
| 26 | Hiển thị kết quả AI | Đạt | Hiển thị nội dung, model, phạm vi dữ liệu và cảnh báo kiểm chứng. |
| 27 | Lỗi/giới hạn AI | Đạt | Timeout, rate limit, lỗi HTTP, phản hồi rỗng/sai cấu trúc và thiếu API key có phản hồi rõ. |
| 28 | Kiểm thử chức năng nghiệp vụ/AI | Một phần | Có 11 API tests gồm đăng nhập, quyền, CRUD, validate và thiếu API key; chưa có PostgreSQL/Gemini thật, UI E2E và kiểm thử tải. |
| 29 | Review code bằng AI | Chưa đạt | Chưa có minh chứng review/refactor AI trong repository. |
| 30 | Trải nghiệm tích hợp AI | Đạt | Có màn hình riêng, câu hỏi gợi ý, loading, phạm vi dữ liệu và xác nhận AI chỉ tư vấn. |
| 31 | Hoàn thiện toàn bộ hệ thống | Một phần | MVP các luồng cốt lõi có; đề tài đầy đủ còn thiếu công đoạn, nhân lực, BOM, kế hoạch/định mức và báo cáo. |
| 32 | Kiến trúc và chất lượng mã | Một phần | Backend chia module, frontend TypeScript strict và production build thành công; chưa có lint/format/check kiến trúc trong CI. |
| 33 | Chất lượng CSDL | Một phần | Có PK/FK/unique/check, seed demo; chưa có migration, lịch sử biến động, backup/restore và xác minh PostgreSQL thật. |
| 34 | Chất lượng UI/UX | Một phần | Responsive và thông báo cơ bản có; chưa kiểm thử trực quan trên trình duyệt/thiết bị hoặc đánh giá người dùng. |
| 35 | Chất lượng AI | Một phần | Prompt grounding, giới hạn và cảnh báo có; chưa benchmark độ chính xác, sai lệch hay tính hữu ích. |
| 36 | Bảo mật, riêng tư, đạo đức AI | Một phần | Hash Argon2, JWT, role guard, API key backend, dữ liệu tối thiểu và AI chỉ đọc; token demo lưu localStorage, chưa có audit/retention/HTTPS triển khai. |
| 37 | Hiệu năng và độ ổn định | Một phần | DB pool kiểm tra kết nối, giới hạn output và timeout; chưa có phân trang, cache, load test hay kiểm tra PostgreSQL/Gemini thật. |
| 38 | Triển khai và đóng gói | Một phần | Có hướng dẫn môi trường, `.env.example`, PostgreSQL Compose; chưa Docker hóa frontend/backend, cloud demo hoặc quy trình backup. |

## Kết quả kiểm tra đã chạy

- `python -m pytest -q`: 11 API tests pass trên SQLite test database.
- `npm run build`: TypeScript check và Vite production build pass.
- `python -m compileall -q backend\app backend\tests`: cú pháp Python pass.
- `docker compose up -d db`: **không hoàn tất** vì không thể kết nối Docker Hub để tải `postgres:16`; vì vậy tích hợp PostgreSQL chưa được xác minh trong môi trường này.
- Gemini: API chưa được gọi thật vì chưa cấu hình `GEMINI_API_KEY`; test kiểm tra lỗi cấu hình thiếu key.

## Việc ưu tiên tiếp theo để nâng điểm

1. Chạy Compose và API với PostgreSQL 16; xác minh seed, CRUD và migration.
2. Tạo prompt benchmark tối thiểu gồm dữ liệu chuẩn, chạy và lưu kết quả thật của ba vòng tối ưu.
3. Hoàn thiện quản lý người dùng, audit log, đổi mật khẩu, backup/restore và bảo vệ triển khai HTTPS.
4. Bổ sung BOM, công đoạn, nhân công, biến động kho và báo cáo cho đúng phạm vi xưởng.
5. Thêm test Gemini mock/real có kiểm soát, UI E2E, review evidence AI và Docker Compose đầy đủ.
