# Nhật ký minh chứng sử dụng AI

Tài liệu này là mẫu ghi nhận minh chứng khi nhóm thực sự dùng công cụ AI. Không ghi prompt/response giả; lưu bản đã ẩn danh và không đưa API key, mật khẩu, dữ liệu cá nhân hoặc dữ liệu sản xuất nhạy cảm vào log.

## A. AI hỗ trợ phân tích và thiết kế

| Lần | Prompt đã dùng | Phản hồi AI (đường dẫn/ảnh đã ẩn danh) | Phần nhóm giữ/chỉnh sửa | Cách kiểm chứng |
|---|---|---|---|---|
| 1 | Yêu cầu đọc báo cáo môn học, trích xuất yêu cầu và đối chiếu repository. | Có bảng actor/FR/NFR/AI/security/test/triển khai trong [REQUIREMENTS_FROM_REPORT.md](./REQUIREMENTS_FROM_REPORT.md). Không lưu API key, dữ liệu nhạy cảm hoặc toàn văn hội thoại. | Nhóm cần xác nhận mâu thuẫn 4/5 role; nội dung được ghi nhận là trích xuất/đối chiếu, không phải quyết định nghiệp vụ cuối cùng. | Đối chiếu nội dung với DOCX trong workspace, model/API/test hiện hành; ghi rõ các tiêu chí chưa đạt/chưa đo. |

## B. AI hỗ trợ lập trình/review

| Lần | Công cụ và prompt | Phản hồi hoặc thay đổi được hỗ trợ | File/commit | Kiểm tra của sinh viên |
|---|---|---|---|---|
| 1 | Phiên Copilot SDK trong VS Code: yêu cầu tiếp tục triển khai backend/API, RBAC 5 role, AI privacy/safety, giao diện React, test và tài liệu theo báo cáo. | Đã hỗ trợ mở rộng entity/API/UI, migration additive, test workflow và tìm lỗi timezone/response trong lúc chạy test. Không coi đây là review độc lập hoặc chứng nhận bảo mật. | Phần triển khai trước đã được đẩy trong commit `9d4bb23`; các thay đổi bổ sung xuất vật tư, tiến độ và giao diện hóa đơn đang ở worktree, chưa commit. Xem các file nguồn ở README và [REQUIREMENTS_FROM_REPORT.md](./REQUIREMENTS_FROM_REPORT.md). | Lần xác minh trước commit: 25 API tests pass; PostgreSQL schema/seed smoke test pass. Lần xác minh hiện tại: 29 test pass trên SQLite, bảng mới đã được kiểm tra trên PostgreSQL local; Python compile và frontend production build pass. Sinh viên cần tự đọc diff, kiểm tra nghiệp vụ và xác nhận từng kết quả trước khi nghiệm thu. |

## C. Kế hoạch tối ưu prompt Gemini (chưa phải kết quả thử nghiệm)

| Vòng | Thay đổi cần thử | Cách so sánh |
|---|---|---|
| 1 — baseline | Prompt hiện tại: vai trò trợ lý, chỉ dùng snapshot, không ghi giao dịch, output theo bốn phần | Chạy bộ câu hỏi chuẩn gồm tồn thấp, ưu tiên đơn, dữ liệu thiếu; chấm đúng dữ liệu và hữu ích |
| 2 — grounding | Yêu cầu trích SKU/mã đơn cụ thể cho mỗi nhận định và nói rõ trường dữ liệu làm căn cứ | So sánh lỗi khẳng định không có căn cứ với vòng 1 |
| 3 — structured output | Yêu cầu JSON có `summary`, `observations`, `recommendations`, `limitations`; validate trước khi render | Đo tỷ lệ parse thành công, nội dung đủ trường và chất lượng tư vấn |

**Trạng thái:** Ba vòng trên vẫn là kế hoạch; chưa có bảng so sánh định lượng hoặc kết quả thử nghiệm tái lập. Tóm tắt phiên trước trong lịch sử workspace ghi nhận một lần gọi Gemini `gemini-3.5-flash-lite` trả thành công; không có log request/response và latency có thể kiểm chứng kèm theo. Phiên hoàn thiện gần đây dùng mock cho API AI, chưa gọi Gemini thật. Không tuyên bố đã hoàn thành tối ưu 3 vòng.

## D. Kiểm chứng AI trong phiên hoàn thiện

- **Prompt kiểm thử:** Gửi câu hỏi nghiệp vụ có email, số điện thoại, họ tên/địa chỉ gắn nhãn và số định danh; kiểm tra payload Gemini mock không chứa các chuỗi nguyên bản hoặc `unit_cost`.
- **Kết quả quan sát:** Test xác nhận các mẫu đó được thay bằng `[REDACTED]`, `unit_cost`/giá vốn không nằm trong payload; prompt jailbreak tiếng Anh/Việt mẫu bị trả HTTP 422; payload vượt giới hạn bị từ chối.
- **Giới hạn:** Đây là test regex trên ví dụ xác định, không phải đánh giá NER/DLP tổng quát hay đo ngưỡng chặn ≥95%/mask 100%. Không gửi API key thật hoặc PII thật trong test.
- **Code liên quan:** [gemini.py](../backend/app/services/gemini.py), [operations_system.txt](../backend/app/prompts/operations_system.txt), các task prompt trong `backend/app/prompts/`, và [test_api.py](../backend/tests/test_api.py).
