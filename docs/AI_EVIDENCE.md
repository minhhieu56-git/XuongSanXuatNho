# Nhật ký minh chứng sử dụng AI

Tài liệu này là mẫu ghi nhận minh chứng khi nhóm thực sự dùng công cụ AI. Không ghi prompt/response giả; lưu bản đã ẩn danh và không đưa API key, mật khẩu, dữ liệu cá nhân hoặc dữ liệu sản xuất nhạy cảm vào log.

## A. AI hỗ trợ phân tích và thiết kế

| Lần | Prompt đã dùng | Phản hồi AI (đường dẫn/ảnh đã ẩn danh) | Phần nhóm giữ/chỉnh sửa | Cách kiểm chứng |
|---|---|---|---|---|
| 1 | Chưa ghi nhận trong repository | Chưa có minh chứng | Điền sau khi có prompt thực tế | Đối chiếu quy trình xưởng và rubric |

## B. AI hỗ trợ lập trình/review

| Lần | Công cụ và prompt | Phản hồi hoặc thay đổi được hỗ trợ | File/commit | Kiểm tra của sinh viên |
|---|---|---|---|---|
| 1 | Chưa ghi nhận trong repository | Chưa có minh chứng | Điền sau khi nhóm sử dụng | Chạy test, review code, kiểm tra phân quyền và dữ liệu biên |

## C. Kế hoạch tối ưu prompt Gemini (chưa phải kết quả thử nghiệm)

| Vòng | Thay đổi cần thử | Cách so sánh |
|---|---|---|
| 1 — baseline | Prompt hiện tại: vai trò trợ lý, chỉ dùng snapshot, không ghi giao dịch, output theo bốn phần | Chạy bộ câu hỏi chuẩn gồm tồn thấp, ưu tiên đơn, dữ liệu thiếu; chấm đúng dữ liệu và hữu ích |
| 2 — grounding | Yêu cầu trích SKU/mã đơn cụ thể cho mỗi nhận định và nói rõ trường dữ liệu làm căn cứ | So sánh lỗi khẳng định không có căn cứ với vòng 1 |
| 3 — structured output | Yêu cầu JSON có `summary`, `observations`, `recommendations`, `limitations`; validate trước khi render | Đo tỷ lệ parse thành công, nội dung đủ trường và chất lượng tư vấn |

**Trạng thái:** API tích hợp trong code; chưa xác nhận gọi Gemini thật và chưa có kết quả ba vòng vì repository chưa được cung cấp API key/dữ liệu chạy. Nhóm cần điền thời điểm, model, input đã ẩn danh, output, lỗi, điểm đánh giá và quyết định sau mỗi vòng trước khi trình bày như minh chứng thực nghiệm.
