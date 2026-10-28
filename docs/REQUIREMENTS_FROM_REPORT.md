# Yêu cầu trích xuất từ báo cáo môn học và đối chiếu mã nguồn

## 1. Nguồn và cách đọc

Nguồn: [Báo Cáo Môn Ứng dung trí tuệ nhân tạo.docx](<../Báo Cáo Môn Ứng dung trí tuệ nhân tạo.docx>).

Tài liệu này tổng hợp nội dung yêu cầu trong các phần khảo sát, tác nhân, yêu cầu chức năng/phi chức năng, kiến trúc, kế hoạch kiểm thử và các sơ đồ Use Case/ERD nhúng. Cột đối chiếu dựa trên code trong repository hiện tại, không coi các tuyên bố kết quả ở báo cáo là bằng chứng kiểm thử nếu repo không có test/log/dữ liệu minh chứng tương ứng.

### Trạng thái đối chiếu

- **Đáp ứng:** Có triển khai nhìn thấy được trong code.
- **Một phần:** Có một phần luồng hoặc khung nền tảng, nhưng chưa đủ phạm vi/tiêu chí.
- **Chưa đáp ứng:** Chưa thấy triển khai trong code hiện tại.
- **Chưa kiểm chứng:** Có mục tiêu đo lường nhưng chưa có kết quả kiểm thử tái lập trong repository.

## 2. Bối cảnh, mục tiêu và phạm vi

Đề tài hướng tới ứng dụng web quản lý tập trung cho xưởng sản xuất nhỏ/vừa (cơ khí, đồ gỗ, may mặc, linh kiện phụ trợ), thay thế bảng trắng, sổ ghi chép, tệp Excel và trao đổi thủ công. Các vấn đề cần giải quyết:

1. Tránh xếp trùng lịch máy móc và ca làm của công nhân.
2. Theo dõi đơn hàng, lệnh sản xuất, công đoạn, sản lượng đạt/lỗi và sự cố.
3. Kiểm soát định mức vật tư (BOM), tiêu hao, hóa đơn và chi phí.
4. Giảm thời gian tổng hợp báo cáo và phản hồi tiến độ khách hàng.
5. Bảo vệ thông tin khách hàng, giá vốn và quy trình kỹ thuật khi sử dụng AI.
6. Dùng AI để tóm tắt ca/sự cố, soạn thông báo tiến độ và diễn giải quy trình/BOM.

Mục tiêu định lượng được nêu gồm CRUD dưới 1,5 giây; AI dưới 5 giây; không trùng lịch; che PII đầy đủ; chặn prompt vi phạm an toàn ít nhất 95%; giảm 70–80% thời gian tổng hợp báo cáo/thông báo. Đây là mục tiêu của báo cáo, không phải kết quả đã được xác nhận trong repository.

## 3. Actor và quyền nghiệp vụ

| Actor theo báo cáo | Nhu cầu/quyền chính | Đối chiếu code hiện tại |
|---|---|---|
| Admin / Quản trị viên | Quản lý tài khoản, RBAC, danh mục dùng chung, khóa/mở tài khoản, audit log | Có API/UI quản lý tài khoản (tạo, đổi role/trạng thái, reset mật khẩu), quản lý một số danh mục, và xem audit log. Chưa có bảng phân quyền cấu hình động; audit không bao phủ mọi thao tác đăng nhập/đọc. |
| Quản đốc / Production Scheduler | Duyệt đơn; lập lệnh, điều độ máy/dây chuyền/nhân công/ca; xem AI; duyệt tin nhắn gửi khách | Có CRUD đơn/tài nguyên/lịch với kiểm tra xung đột và ba luồng AI nghiệp vụ. Chưa có trạng thái duyệt đơn riêng hoặc workflow duyệt/gửi thông báo. |
| Công nhân / kỹ thuật viên | Xem lịch được giao; nhập sản lượng đạt/lỗi; báo sự cố; tra cứu BOM/quy trình | Có thể xem lịch/đơn được giao, tra cứu BOM/công đoạn, ghi nhật ký sản lượng/sự cố và lỗi chất lượng. Chưa có giao diện timeline hoặc quy trình KCS nhiều bước. |
| Kế toán vật tư & chi phí | Quản lý BOM/giá vốn, hóa đơn, chi phí, thanh toán, báo cáo | Có role `accountant`, quyền đọc kho/đơn liên quan tài chính, CRUD chi phí, hóa đơn/thanh toán và báo cáo tài chính ngày tùy chọn. Chưa có costing tự động từ BOM hoặc báo cáo lợi nhuận sản xuất. |
| Khách hàng / đại lý | Tạo/điều chỉnh/hủy đơn, tra cứu tiến độ, nhận cập nhật, hỏi AI | Có role `customer`; xem đơn/hóa đơn trong hồ sơ liên kết, tạo đơn yêu cầu, chỉnh/hủy đơn đang chờ. Chưa có gửi tin/kênh thông báo, phần trăm tiến độ hoặc AI portal khách hàng. |

Tài liệu có chỗ nói RBAC 4 vai trò, chỗ khác xác định 5 vai trò. Phần code hiện chọn 5 role (`admin`, `manager`, `worker`, `accountant`, `customer`) theo danh sách actor/use case; mâu thuẫn gốc vẫn cần giảng viên/chủ sản phẩm xác nhận khi nghiệm thu.

## 4. Yêu cầu chức năng và đối chiếu từng yêu cầu

### 4.1. Quản trị hệ thống và xác thực

| ID | Yêu cầu trích xuất | Đối chiếu code hiện tại |
|---|---|---|
| FR-AUTH-01 | Người dùng đăng nhập bằng tài khoản an toàn. | **Đáp ứng một phần:** API email/mật khẩu, hash Argon2 và JWT trong [security.py](../backend/app/core/security.py), [routes.py](../backend/app/api/routes.py). |
| FR-AUTH-02 | Đăng xuất. | **Đáp ứng một phần:** UI xóa JWT phía trình duyệt; không có thu hồi token/session phía server. |
| FR-AUTH-03 | Đổi mật khẩu và khôi phục/cấp lại mật khẩu. | **Đáp ứng một phần:** User đổi mật khẩu bằng mật khẩu hiện tại; admin reset mật khẩu qua màn hình tài khoản. Chưa có luồng quên mật khẩu/email reset. |
| FR-AUTH-04 | RBAC chi tiết theo quyền xem/thêm/sửa/xóa và 5 actor. | **Đáp ứng một phần:** Đã có 5 role và kiểm tra quyền/scope ở backend, gồm dữ liệu riêng của customer/worker. Ma trận chưa cấu hình động; một số quyền đọc vẫn có thể tinh chỉnh. Xem [entities.py](../backend/app/models/entities.py), [operations.py](../backend/app/api/operations.py). |
| FR-AUTH-05 | Admin tạo tài khoản, cấp lại mật khẩu, khóa/mở khóa user. | **Đáp ứng:** API/UI admin tạo tài khoản, cập nhật role/trạng thái, reset mật khẩu và xóa tài khoản chưa bị dữ liệu nghiệp vụ tham chiếu; không thể tự xóa, tự hạ quyền hoặc tự vô hiệu hóa tài khoản đang đăng nhập. |
| FR-AUTH-06 | Ghi Audit Logs để truy vết thao tác. | **Đáp ứng một phần:** Có bảng/model, admin xem log và ghi nhận các thay đổi tài khoản/đơn/kho/module mới. Chưa phải audit trail bất biến/toàn diện; đăng nhập và một số luồng đọc không ghi log. |
| FR-AUTH-07 | Cấu hình các danh mục dùng chung/thông số hệ thống. | **Chưa đáp ứng:** Chưa có module cấu hình danh mục công đoạn, thông số kỹ thuật hoặc cài đặt nghiệp vụ. |

### 4.2. Công nhân, máy móc, dây chuyền và ca làm

| ID | Yêu cầu trích xuất | Đối chiếu code hiện tại |
|---|---|---|
| FR-RES-01 | Quản lý hồ sơ công nhân: mã, tên, điện thoại, bậc thợ/chuyên môn, trạng thái. | **Đáp ứng một phần:** Có CRUD API/UI, unique worker code và liên kết tài khoản; worker chỉ xem hồ sơ được liên kết. Chưa có phân cấp tay nghề/chấm công. |
| FR-RES-02 | Quản lý máy móc: mã, tên, dây chuyền/phòng và trạng thái sẵn sàng/vận hành/bảo trì/hỏng. | **Đáp ứng một phần:** Có CRUD và trạng thái available/operating/maintenance/broken; chưa có lịch sử bảo trì hoặc phòng ban riêng. |
| FR-RES-03 | Quản lý dây chuyền sản xuất. | **Đáp ứng một phần:** Có CRUD dây chuyền và liên kết máy/lịch; chưa có báo cáo hiệu suất theo dây chuyền. |
| FR-RES-04 | Cấu hình ca làm và lịch công nhân/máy. | **Đáp ứng một phần:** Có CRUD ca/lịch và backend chặn khoảng giao nhau cùng công nhân hoặc máy; test tuần tự đạt. Chưa có timeline UI hoặc bài test cạnh tranh đồng thời. |
| FR-RES-05 | Tra cứu danh mục/quy trình kỹ thuật và bảng giá gia công. | **Đáp ứng một phần:** Có BOM và các công đoạn/hướng dẫn; chưa có catalog sản phẩm/bảng giá chuẩn hóa hoặc workflow quản lý phiên bản kỹ thuật. |

### 4.3. Đơn hàng, lệnh sản xuất và điều độ

| ID | Yêu cầu trích xuất | Đối chiếu code hiện tại |
|---|---|---|
| FR-ORD-01 | Khách đặt đơn trực tuyến hoặc quản đốc tạo đơn; lưu sản phẩm, số lượng, quy cách và ngày mong muốn. | **Đáp ứng một phần:** Manager tạo đơn; customer liên kết hồ sơ có thể tạo yêu cầu và chỉ xem đơn của mình. Chưa có trường quy cách/sản phẩm riêng hoặc phê duyệt tiếp nhận. |
| FR-ORD-02 | Tiếp nhận, duyệt, yêu cầu điều chỉnh hoặc hủy đơn hàng. | **Đáp ứng một phần:** Customer chỉnh/hủy đơn `planned`, manager có thể cập nhật trạng thái. Chưa có trạng thái chờ duyệt riêng, yêu cầu chỉnh sửa và quyết định duyệt/audit tương ứng. |
| FR-ORD-03 | Lập lệnh sản xuất, gán công nhân, máy, dây chuyền và giờ bắt đầu/kết thúc. | **Đáp ứng một phần:** `work_schedules` gán đơn/công nhân/máy/dây chuyền/ca và khoảng thời gian; chưa có lệnh sản xuất tách khỏi đơn. |
| FR-ORD-04 | Tự động phát hiện xung đột thời gian của máy hoặc công nhân; không xếp hai lệnh chồng giờ. | **Đáp ứng một phần:** API kiểm tra overlap half-open theo cùng worker/machine, bỏ qua lịch hủy/hoàn thành; PostgreSQL dùng advisory transaction lock. Test overlap tuần tự pass; chưa đo/kiểm thử đồng thời nhiều connection. |
| FR-ORD-05 | Theo dõi vòng đời lệnh `SCHEDULED → IN_PROGRESS → COMPLETED/CANCELLED`; khách xem trạng thái và % hoàn thành. | **Đáp ứng một phần:** Có trạng thái lịch và đơn; customer xem trạng thái đơn của mình. Chưa có tiến độ phần trăm, giao hàng hoặc trạng thái duyệt riêng. |
| FR-ORD-06 | Khách yêu cầu đổi/hủy; quản đốc duyệt thay đổi. | **Đáp ứng một phần:** Customer có thể cập nhật/hủy đơn đang `planned`; manager có thể quản lý đơn. Chưa có hộp thư/yêu cầu thay đổi và luồng duyệt khách hàng riêng. |

### 4.4. Tiến độ, chất lượng, nhật ký và BOM

| ID | Yêu cầu trích xuất | Đối chiếu code hiện tại |
|---|---|---|
| FR-PROD-01 | Theo dõi công đoạn (ví dụ cắt, phay/gia công, lắp ráp, sơn, KCS). | **Đáp ứng một phần:** Có công đoạn theo thứ tự trên đơn, trạng thái và hướng dẫn; chưa có theo dõi thời lượng/định mức thời gian và quy trình nhiều phiên bản. |
| FR-PROD-02 | Công nhân nhập sản lượng đạt và sản lượng lỗi/KCS theo ca/công đoạn. | **Đáp ứng một phần:** Công nhân được phân công ghi sản lượng đạt/lỗi theo đơn/công đoạn/ca; backend chặn ghi ngoài đơn phân công và chặn vượt số lượng đơn theo công đoạn. Chưa có dashboard tỷ lệ lỗi hoặc đơn vị KCS độc lập. |
| FR-PROD-03 | Ghi nhật ký vận hành, ghi chú ca, sự cố hỏng máy, thiếu vật tư/gián đoạn. | **Đáp ứng một phần:** Có nhật ký theo ca, worker, máy, ghi chú/loại sự cố; chưa có workflow xử lý sự cố/ảnh đính kèm. |
| FR-PROD-04 | Quản lý BOM: vật tư, đơn vị, đơn giá nhập, định mức tiêu hao trên mỗi sản phẩm và tiêu hao thực tế. | **Đáp ứng một phần:** BOM liên kết vật tư và định mức; quản đốc có thể xuất phần vật tư còn thiếu theo BOM, kiểm tra tồn kho nguyên tử, trừ tồn và lưu lịch sử xuất. Thiếu một vật tư thì toàn bộ giao dịch bị từ chối. Chưa có xuất từng phần, hoàn trả vật tư hoặc tính giá thành tự động. |
| FR-PROD-06 | Theo dõi tỷ lệ hoàn thành công đoạn và tiến độ đơn. | **Đáp ứng một phần:** API tính tiến độ trung bình từ sản lượng đạt/lỗi của các công đoạn; khách hàng xem phần trăm trong danh sách đơn và AI bản nháp được cấp cùng tiến độ. Công thức trung bình cần chủ sản phẩm xác nhận; chưa có biểu đồ/timeline hoặc tiến độ theo thời gian. |
| FR-PROD-05 | KCS, trạng thái máy, thiếu hụt vật tư và sự cố được thể hiện để quản đốc xử lý. | **Đáp ứng một phần:** Có trạng thái máy, cảnh báo tồn, defect và nhật ký sự cố; chưa có workflow KCS/khắc phục hoặc bảo trì. |

### 4.5. Tài chính, hóa đơn, thanh toán và báo cáo

| ID | Yêu cầu trích xuất | Đối chiếu code hiện tại |
|---|---|---|
| FR-FIN-01 | Lập hóa đơn từ số lượng hoàn thành, đơn giá gia công và chi phí BOM. | **Đáp ứng một phần:** Hóa đơn tính số lượng đơn × đơn giá dịch vụ, chiết khấu; chưa gộp chi phí BOM/tự động tính từ sản lượng hoàn thành. |
| FR-FIN-02 | Chiết khấu/giảm giá, phương thức tiền mặt/chuyển khoản, trạng thái thanh toán/công nợ. | **Đáp ứng một phần:** Có chiết khấu, tiền mặt/chuyển khoản, thanh toán một phần/đầy đủ và chặn vượt số dư. Chưa hỗ trợ hoàn tiền/void giao dịch đã thu. |
| FR-FIN-03 | Báo cáo doanh thu ngày/tháng/năm. | **Đáp ứng một phần:** Có API/UI báo cáo hóa đơn, doanh thu đã lập/đã thu/còn phải thu/chi phí, lọc ngày tùy chọn. Chưa có preset lịch tháng/năm, export hoặc đối soát. |
| FR-FIN-04 | Báo cáo chi phí vật tư, sản lượng, tỷ lệ lỗi KCS và hiệu suất máy. | **Đáp ứng một phần:** Có báo cáo khoản chi, nhật ký sản lượng/lỗi và lịch sử xuất vật tư; chưa có quy đổi chi phí xuất vật tư, báo cáo hiệu suất máy hoặc tỷ lệ lỗi tổng hợp. |
| FR-FIN-05 | Kế toán xem/xác nhận giao dịch thanh toán. | **Đáp ứng một phần:** Role accountant được tạo/xem thanh toán và hóa đơn qua backend/UI; chưa có workflow đối soát/xác nhận ngân hàng. |

### 4.6. Chức năng AI nghiệp vụ

| ID | Yêu cầu trích xuất | Đối chiếu code hiện tại |
|---|---|---|
| FR-AI-01 | Tóm tắt nhật ký ca thành báo cáo sản lượng đạt/lỗi, sự cố thiết bị và đề xuất xử lý cho quản đốc. | **Đáp ứng một phần:** Endpoint/prompt/UI tóm tắt nhật ký theo ca; dữ liệu tối đa 100 log và chưa có workflow phê duyệt báo cáo hay kiểm thử Gemini thật trong phiên này. |
| FR-AI-02 | Sinh tin nhắn tiến độ cá nhân hóa gồm % công đoạn/ngày giao dự kiến để quản đốc duyệt trước khi gửi Zalo/SMS/Email. | **Đáp ứng một phần:** Sinh bản nháp có tiến độ phần trăm từ các công đoạn, trạng thái và hạn đơn; yêu cầu kiểm duyệt. Chưa lưu phiên bản/duyệt, chưa tích hợp gửi kênh và không dự đoán ngày hoàn thành. |
| FR-AI-03 | Giải thích quy trình kỹ thuật, thông số vận hành và BOM bằng ngôn ngữ dễ hiểu; kèm technical disclaimer. | **Đáp ứng một phần:** Prompt riêng lấy dữ liệu BOM/công đoạn và có cảnh báo chuyên môn; chất lượng đầu ra chưa được đánh giá chuyên gia, không cung cấp thông số an toàn chưa cấu hình. |
| FR-AI-04 | Hỏi đáp/nhận xét tình hình đơn và tồn kho từ dữ liệu hệ thống. | **Đáp ứng:** Có AI analysis đọc dữ liệu tồn kho/đơn qua [gemini.py](../backend/app/services/gemini.py), UI tại [App.tsx](../frontend/src/App.tsx). |
| FR-AI-05 | Trợ lý AI chỉ hỗ trợ; không tự ghi hoặc thay đổi nghiệp vụ. | **Đáp ứng:** Endpoint AI chỉ đọc context và trả lời; không có công cụ ghi dữ liệu được cấp cho model. |

### 4.7. Use case bổ sung trích từ sơ đồ nhúng

Các sơ đồ hình còn thể hiện use case ngoài phần mô tả chức năng bằng văn bản. Những use case này cũng cần được tính khi hoàn thiện yêu cầu:

| Actor | Use case trong sơ đồ | Đối chiếu code hiện tại |
|---|---|---|
| Công nhân/kỹ thuật viên | Lập/xem lịch sản xuất; xem lệnh được giao. | **Đáp ứng một phần:** Xem lịch và đơn theo worker profile; chỉ manager/admin tạo hoặc sửa lịch. |
| Công nhân/kỹ thuật viên | Ghi nhận thông số kỹ thuật và nhật ký ca. | **Đáp ứng một phần:** Có log sản lượng, ghi chú, sự cố theo ca/công đoạn; chưa có trường đo kỹ thuật cấu hình. |
| Công nhân/kỹ thuật viên | Kiểm tra lỗi sản phẩm KCS; ghi nhận sản lượng lỗi. | **Đáp ứng một phần:** Ghi sản lượng lỗi và defect; chưa có các bước KCS/duyệt khắc phục. |
| Công nhân/kỹ thuật viên | Tra cứu định mức vật tư BOM và AI giải thích quy trình kỹ thuật. | **Đáp ứng một phần:** Có API/UI BOM và AI giải thích cấu hình hiện có; chưa có catalog/quy trình đầy đủ. |
| Công nhân/kỹ thuật viên | AI tóm tắt hồ sơ/tình hình vận hành. | **Đáp ứng một phần:** Có API tóm tắt ca, nhưng chỉ manager/admin được gọi; chưa mở AI ca cho worker. |
| Công nhân/kỹ thuật viên | AI phân tích hiệu suất dây chuyền. | **Chưa đáp ứng:** Không có dữ liệu thời gian/sản lượng theo dây chuyền. |
| Công nhân/quản đốc | AI chẩn đoán sự cố máy; dự báo bảo trì máy. | **Chưa đáp ứng:** Không có hồ sơ máy, sự cố hoặc lịch sử bảo trì. |
| Admin | Quản lý tài nguyên xưởng, quyền; quản lý máy móc; xem audit log. | **Đáp ứng một phần:** Có user administration, RBAC backend, CRUD tài nguyên và audit view; chưa có permission matrix động và audit đầy đủ. |
| Quản đốc | Duyệt đơn; lập lệnh và phân công; tự kiểm tra lịch trùng. | **Đáp ứng một phần:** Có phân công, chống overlap và CRUD đơn; thiếu quy trình duyệt đơn/lệnh riêng. |
| Quản đốc | AI tóm tắt ca và soạn tin nhắn tiến độ. | **Đáp ứng một phần:** Có API/UI và prompt cho tóm tắt ca/bản nháp tiến độ; không gửi tự động hoặc lưu duyệt. |
| Kế toán | Quản lý BOM; lập hóa đơn/chi phí; xác nhận thanh toán. | **Đáp ứng một phần:** Có role accountant, hóa đơn, chi phí, thanh toán; BOM do manager quản lý, chưa có đối soát. |
| Kế toán | Xem báo cáo doanh thu, chi phí và sản lượng. | **Đáp ứng một phần:** Có báo cáo financial theo khoảng ngày; chưa có phân tích sản lượng/hiệu suất máy trong báo cáo tài chính. |
| Khách hàng | Đặt đơn; tra cứu tiến độ; yêu cầu đổi/hủy. | **Đáp ứng một phần:** Portal role-scoped xem/đặt/chỉnh/hủy yêu cầu đang chờ; chưa có duyệt đơn, % tiến độ hoặc cập nhật giao hàng. |
| Khách hàng | AI giải thích sản phẩm/quy trình; nhận tin tiến độ. | **Chưa đáp ứng:** Không có catalog, customer channel hoặc integration gửi tin. |

## 5. Yêu cầu công nghệ và kiến trúc

| Yêu cầu trong báo cáo | Đối chiếu code hiện tại |
|---|---|
| Web application theo kiến trúc nhiều lớp/3-tier. | **Đáp ứng một phần:** React UI, FastAPI routes/services, SQLAlchemy/PostgreSQL và Gemini service được tách lớp; chưa có đầy đủ workflow mục tiêu. |
| Frontend React + Vite, responsive cho desktop/tablet/màn hình xưởng. | **Đáp ứng một phần:** Có React, Vite, TypeScript, trang vận hành và CSS breakpoint; chưa có bảng lịch/timeline điều độ hoặc kiểm thử tablet/màn hình giám sát. |
| Backend Python + FastAPI, RESTful API. | **Đáp ứng:** FastAPI API endpoints và request/response schema. |
| PostgreSQL 16 tập trung, ORM SQLAlchemy, dữ liệu được chuẩn hóa/index. | **Đáp ứng một phần:** SQLAlchemy có PK/FK/unique/check/index; additive bootstrap migration đã chạy/kiểm tra trên PostgreSQL 16. Chưa có migration versioned (Alembic), backup/restore hoặc đánh giá tải. |
| Google Gemini API. | **Đáp ứng:** Tích hợp server-side `generateContent`; model lấy từ cấu hình môi trường. Việc quyền/model có thể phụ thuộc API key. |
| REST API giữa frontend/backend và dịch vụ AI. | **Đáp ứng một phần:** Có JSON API, frontend proxy và HTTP Gemini. HTTPS giữa browser/API chỉ có thể được đảm bảo khi triển khai sau TLS termination; dev local dùng HTTP. |
| Docker đóng gói hệ thống. | **Chưa triển khai trong phạm vi lần này:** Người dùng yêu cầu không dùng Docker Compose; backend/frontend không có Dockerfile. |
| Lưu trữ tập trung dữ liệu user, worker, customer, machines, lines, schedules, orders, logs/details, materials/BOM, invoices, audit logs. | **Đáp ứng một phần:** Các entity nêu trên cùng lịch sử xuất vật tư theo đơn đã có trong SQLAlchemy/PostgreSQL; audit trail vẫn chưa bất biến/toàn diện. |

## 6. Yêu cầu AI, prompt và bảo vệ dữ liệu

### 6.1. Phạm vi và luồng AI

- Đề án chọn Google Gemini API cho tóm tắt nhật ký ca, sinh thông báo tiến độ và giải thích quy trình/BOM.
- Dữ liệu gửi AI phải lấy từ hệ thống, được giới hạn đúng mục đích và qua backend; API key không đặt trong trình duyệt.
- Code gọi Gemini từ backend; API key đọc từ `.env`, không nằm trong frontend. Context được giới hạn tối đa 200 inventory/orders, 100 log/ca hoặc 200 BOM/công đoạn mỗi nhóm; payload quá dài bị từ chối.
- Có system/task prompt riêng cho tóm tắt ca, bản nháp tiến độ khách hàng và giải thích kỹ thuật/BOM; có phân tích đơn/kho. Không tích hợp kênh gửi tin, workflow duyệt hoặc gọi Gemini thật trong bài test.
- Nếu không cấu hình API key, hệ thống dùng phân tích quy tắc nội bộ; UI/API có thể phân biệt nguồn Gemini với nguồn local.
- GenAI còn được đề xuất hỗ trợ SDLC: phân tích yêu cầu/use case, thiết kế CSDL, sinh CRUD, tối ưu kiểm tra lịch, thiết kế safety prompts, kiểm thử PII và hỗ trợ đóng gói Docker. Đây là hoạt động phát triển dự án; repository hiện không có nhật ký prompt/phản hồi đầy đủ chứng minh các hoạt động này đã diễn ra.

### 6.2. Safety guardrails

Yêu cầu báo cáo:

1. System prompt chặn hướng dẫn trái quy trình an toàn lao động.
2. Không cho AI thay đổi thông số máy nguy hiểm hoặc định mức BOM.
3. Phản kháng prompt injection/jailbreak, đặc biệt khi người dùng hỏi dữ liệu/giá vốn ngoài quyền.
4. Kết quả AI có disclaimer bắt buộc: “Thông tin do AI tạo ra chỉ mang tính chất tham khảo hành chính, không thay thế chỉ định chuyên môn của Quản đốc/Kỹ thuật viên xưởng”.
5. AI không tự thực hiện giao dịch; người có thẩm quyền kiểm chứng kết quả.

Đối chiếu:

- **Đáp ứng một phần:** System prompt grounding, coi text trong JSON là dữ liệu, không sửa giao dịch, không hướng dẫn bỏ bảo hộ/an toàn hoặc thay thông số máy/BOM; task prompts có giới hạn theo nghiệp vụ. Chưa có kiểm định chuyên gia/kiểm tra đầu ra nguy hiểm toàn diện.
- **Đáp ứng một phần:** Heuristic chặn một số câu jailbreak tiếng Anh/Việt; có test ví dụ, không có bộ adversarial đại diện hoặc tỷ lệ chặn đo được.
- **Đáp ứng:** Backend gắn disclaimer theo yêu cầu vào Gemini và local fallback; giao diện cũng nhắc kiểm chứng.
- **Đáp ứng:** Mô hình không được cấp quyền thực hiện CRUD; thao tác do người dùng thực hiện riêng qua API có RBAC.

### 6.3. PII masking và dữ liệu nhạy cảm

Báo cáo yêu cầu trước khi gửi Gemini phải che/mã hóa 100%:

- Họ tên khách hàng.
- Số điện thoại.
- Địa chỉ giao hàng.
- CCCD/định danh cá nhân.
- Đơn giá vốn/chi phí nhạy cảm.

**Đối chiếu: Đã có data minimization/masking một phần, chưa chứng minh đạt 100%.** `unit_cost` bị loại khỏi prompt context; context AI không lấy tên/điện thoại/địa chỉ khách; email, điện thoại, chuỗi số 9–12 chữ số và tên/địa chỉ có nhãn rõ trong prompt được che. Test mock xác nhận các mẫu này không rời backend. Regex không nhận diện mọi dạng tên/địa chỉ/CCCD; không coi kết quả này là đạt 100% masking. Dữ liệu thật nhạy cảm vẫn cần DLP/NER hoặc policy chặt hơn trước production.

## 7. Yêu cầu phi chức năng, bảo mật và UX

| ID | Yêu cầu/giới hạn trong báo cáo | Đối chiếu code hiện tại |
|---|---|---|
| NFR-PERF-01 | CRUD phổ biến dưới 1,5 giây. | **Chưa kiểm chứng:** Không có benchmark hoặc đo latency tự động. |
| NFR-PERF-02 | Gemini trả lời dưới 5 giây. | **Chưa đáp ứng/chưa kiểm chứng:** Client có timeout tới 30 giây; không có SLA/benchmark dưới 5 giây. |
| NFR-SCALE-01 | Chịu 50–100 user đồng thời trong giờ cao điểm. | **Chưa kiểm chứng:** Không có load test, pooling/tuning hay số liệu concurrency. |
| NFR-SEC-01 | Mật khẩu hash bcrypt hoặc PBKDF2. | **Đáp ứng mục tiêu bảo vệ ở mức thuật toán:** Code dùng Argon2 qua `pwdlib`, là password hashing chuyên dụng; thuật toán khác lựa chọn ví dụ trong báo cáo. |
| NFR-SEC-02 | HTTPS/TLS cho frontend-backend và AI. | **Đáp ứng một phần:** Gemini dùng HTTPS; môi trường local browser/API dùng HTTP. Chưa có cấu hình TLS triển khai. |
| NFR-SEC-03 | PII masking đạt 100% trước API AI. | **Đáp ứng một phần, chưa đạt/chưa chứng minh 100%:** Bỏ giá vốn, không truy xuất PII khách vào context và che một số mẫu định danh; regex không phải NER/DLP tổng quát. |
| NFR-SEC-04 | RBAC bảo vệ dữ liệu và chức năng nhạy cảm. | **Đáp ứng một phần:** Có 5 role, guard backend, customer/worker scoping và kiểm thử; chưa có ma trận quyền cấu hình động, audit toàn diện hoặc review độc lập. |
| NFR-AI-01 | Guardrails về an toàn máy, lao động, BOM. | **Đáp ứng một phần:** System/task prompts cấm hướng dẫn bỏ quy trình an toàn/thay thông số và AI chỉ đọc; chưa có kiểm tra output hoặc safety review chuyên gia. |
| NFR-AI-02 | Disclaimer kỹ thuật cố định cho mọi kết quả AI liên quan. | **Đáp ứng:** Backend gắn nguyên văn disclaimer cho phản hồi Gemini/local; vẫn cần kiểm tra trực tiếp bằng model thật theo từng prompt. |
| NFR-AI-03 | Chặn jailbreak/adversarial prompts ít nhất 95%. | **Chưa kiểm chứng:** Không có red-team test set hoặc report; không thể khẳng định tỷ lệ đạt. |
| NFR-UX-01 | UI trực quan, dạng lịch/timeline/card, desktop/tablet/màn hình giám sát. | **Đáp ứng một phần:** Có card, bảng và responsive breakpoint; thiếu lịch/timeline và kiểm thử thiết bị. |
| NFR-UX-02 | Validate client/server; lỗi tiếng Việt rõ; chặn SĐT sai, lịch quá khứ và sản lượng âm. | **Đáp ứng một phần:** Pydantic kiểm tra input, khoảng lịch, sản lượng không âm/dương theo nghiệp vụ, foreign keys và conflict; phone vẫn là chuỗi tự do, chưa áp dụng quy tắc chuẩn hóa SĐT. |
| NFR-REL-01 | Xử lý timeout, rate limit, lỗi model, nội dung rỗng/sai định dạng. | **Đáp ứng một phần:** Có timeout, xử lý 429, lỗi HTTP/model và nội dung rỗng; chưa có retry/backoff hoặc giám sát vận hành. |
| NFR-DATA-01 | CSDL chuẩn hóa, toàn vẹn quan hệ và có chỉ mục. | **Đáp ứng một phần:** Có schema/ràng buộc/index và additive bootstrap migration đã kiểm tra trên PostgreSQL; chưa có Alembic/versioning, backup/restore hoặc kiểm thử khôi phục. |

## 8. Tiêu chí đánh giá và kết quả báo cáo nêu

### 8.1. Ngưỡng/mục tiêu cần chứng minh

| Tiêu chí | Ngưỡng theo tài liệu | Trạng thái theo repository |
|---|---:|---|
| Thời gian phản hồi CRUD | `< 1,5 giây` | Chưa có benchmark; chưa xác nhận. |
| Thời gian phản hồi AI | `< 5 giây` | Chưa có benchmark; timeout cấu hình lớn hơn ngưỡng này. |
| Người dùng đồng thời | `50–100` | Chưa có load test. |
| Xung đột lịch máy/công nhân | `0%` | Có kiểm tra overlap và test API tuần tự; chưa có concurrent/load test để xác nhận tỷ lệ 0% dưới tranh chấp thực tế. |
| PII được mask trước khi gọi AI | `100%` | Có test mock xác nhận email/phone/ID/name/address theo mẫu và loại giá vốn; không chứng minh mọi PII đều được phát hiện nên ngưỡng 100% chưa đạt/chưa xác nhận. |
| Jailbreak/adversarial bị chặn | `≥ 95%` | Chưa có test set hoặc kết quả chạy. |
| Thời gian tổng hợp báo cáo/thông báo tiết kiệm | `70–80%` | Chưa có phép đo trước/sau hay workflow báo cáo tự động. |
| Đầu vào sai bị chặn và báo lỗi tiếng Việt | Yêu cầu theo từng biểu mẫu | Có Pydantic/DB constraints và test các trường hợp quan trọng; chưa phủ hết biên cho mọi resource. |
| Tính đúng nghiệp vụ/E2E | Đơn → lịch → tiến độ/sự cố → AI → thanh toán | Có API tests theo từng workflow/module trên SQLite; chưa có full E2E trình duyệt/production DB từ đầu đến cuối. |

### 8.2. Những số liệu báo cáo tự tuyên bố

Báo cáo ghi CRUD trung bình `0,85 giây`, GenAI trung bình `2,6 giây`, masking `100%`, jailbreak `97,5%` và mức hoàn thành nghiệp vụ `100%`. Các số này được ghi nhận ở đây như **tuyên bố trong tài liệu nguồn**, không phải số liệu đã xác minh: repository không có raw test results, benchmark scripts, mẫu/red-team dataset, log masking hay kịch bản nghiệm thu đủ để tái lập các kết quả đó.

## 9. Kế hoạch và môi trường kiểm thử theo báo cáo

### 9.1. Kiểm thử cần thực hiện

1. Unit/integration test cho đăng nhập, RBAC, CRUD và validation.
2. Kiểm thử điều độ: hai lệnh cùng máy hoặc cùng công nhân có khoảng thời gian chồng nhau phải bị từ chối.
3. Kiểm thử tính toán sản lượng đạt/lỗi, BOM, tiêu hao, hóa đơn, chiết khấu và thanh toán.
4. E2E từ đặt/duyệt đơn → phân công → cập nhật tiến độ/sự cố → AI → hóa đơn/thanh toán.
5. Kiểm tra Gemini: tóm tắt nhật ký, sinh thông báo, giải thích kỹ thuật; lỗi mạng, timeout, rate limit, model lỗi, output rỗng.
6. PII test: xác nhận tên, điện thoại, địa chỉ, CCCD và giá vốn đã mask trước khi request rời backend.
7. AI red teaming: jailbreak, yêu cầu bỏ qua system prompt, yêu cầu hướng dẫn thao tác nguy hiểm, lấy giá vốn/PII; tính tỷ lệ chặn trên bộ test đã xác định.
8. Performance/load test theo ngưỡng ở mục 8.1.
9. Kiểm tra giao diện Web desktop và tablet/màn hình giám sát.

### 9.2. Môi trường được báo cáo đề xuất

- Server: Ubuntu 22.04 LTS, CPU 4 cores, RAM 8 GB.
- Python 3.11, FastAPI, PostgreSQL 16.
- Client: Chrome 126+ trên desktop và tablet Android/iPad.
- AI: Google Gemini API với PII masking nội bộ.

### 9.3. Test hiện có trong repository

Trong [test_api.py](../backend/tests/test_api.py) có 30 API tests: health/login/change-password, RBAC 5 role và customer scope, CRUD đơn/kho, user/audit (gồm tạo, cập nhật và xóa tài khoản với kiểm tra quyền), worker/máy/dây chuyền/ca/lịch overlap, BOM/xuất vật tư/công đoạn/log/defect/tiến độ, invoice/payment/expense/financial report và duplicate invoice, AI fallback/task, PII masking mock, prompt-injection mẫu, context quá lớn và lỗi Gemini.

Kết quả xác minh gần nhất: **30 backend tests pass**, Python `compileall` pass, frontend `npm run build` pass; bảng `material_issues` và check constraint xuất vật tư được kiểm tra trên PostgreSQL 16 thực tế. Các schema/enum/invoice checks và demo seed đã được kiểm tra trong phiên triển khai trước. Đây không phải benchmark, full E2E, đánh giá model Gemini thật, red-team coverage hay kiểm thử đồng thời.

## 10. Kế hoạch triển khai 9 tuần trong báo cáo

| Giai đoạn báo cáo | Công việc và đầu ra đề xuất | Đối chiếu code hiện tại |
|---|---|---|
| Tuần 1–2: khảo sát/thiết kế | Khảo sát nghiệp vụ, dùng AI hỗ trợ yêu cầu/use case; thiết kế ERD, DDL, seed, wireframe; hoàn thành mốc KT1. | Có tài liệu phân tích và code MVP; không có bằng chứng tái lập cho toàn bộ lịch sử AI/KT1; ERD trong DOCX có điểm không nhất quán. |
| Tuần 3: nền tảng | FastAPI, PostgreSQL, React; CRUD công nhân/máy/khách hàng; UI RBAC 5 role. | Có các entity/API/UI, năm role và backend guards; chưa có ma trận quyền động hoặc review độc lập. |
| Tuần 4: đơn và điều độ | Đặt/duyệt đơn, lệnh sản xuất, BOM, phân công; thuật toán chặn lịch trùng. | Có customer order flow cơ bản, BOM, schedule và overlap validation; chưa có duyệt đơn/lệnh riêng hoặc concurrent load test. |
| Tuần 5: tiến độ/tài chính | Ghi nhận sản lượng, sự cố; hóa đơn/chi phí/thống kê; unit test, KT2. | Có log/defect/invoice/payment/expense/financial report, xuất vật tư từ BOM và API tests; chưa có hoàn trả vật tư, KCS đầy đủ hoặc báo cáo hiệu suất máy. |
| Tuần 6: AI và privacy | Gemini, PII masking, prompt cho tóm tắt ca/thông báo/kỹ thuật và disclaimer. | Có ba prompt nghiệp vụ, data minimization/masking heuristic và disclaimer; chưa chứng minh PII 100% hoặc kiểm nghiệm Gemini thật. |
| Tuần 7: an toàn AI | Red-team jailbreak, tối ưu prompt, UI kết quả, KT3. | Có bộ lọc heuristic và test mẫu injection; chưa có red-team dataset/metric 95% hoặc 3 vòng tối ưu được ghi bằng chứng. |
| Tuần 8: kiểm thử tích hợp | E2E toàn bộ luồng nghiệp vụ, bug fixing, hiệu năng, UX và báo cáo rủi ro AI. | 29 API tests và production build pass; chưa có E2E trình duyệt, load test hoặc benchmark. |
| Tuần 9: triển khai | Dockerize, setup/triển khai, tài liệu và nghiệm thu. | README và seed/migration bootstrap có; Docker Compose không dùng theo yêu cầu, chưa có Dockerfile/TLS/deployment pipeline. |

Kế hoạch nguồn đặt thời gian 27/07/2026–27/09/2026, 9 tuần và 2 thành viên kiêm nhiệm.

## 11. Các điểm cần làm rõ trong tài liệu nguồn

1. RBAC được mô tả lúc là 4 role, các bảng khảo sát/actor/use case/architecture lại dùng 5 role.
2. Sơ đồ use case tổng quan và các sơ đồ phân rã có cách gán actor/use case chưa hoàn toàn thống nhất với phần mô tả bằng văn bản; dùng danh sách actor và FR bằng văn bản làm căn cứ cho bảng đối chiếu.
3. Sơ đồ ERD nhúng có các tên miền không phù hợp bài toán xưởng chung như `DENTAL_CHAIRS`, `DOCTOR_SCHEDULES`, đồng thời `MACHINES` xuất hiện lặp. Cần làm lại ERD thống nhất trước khi dùng làm DDL/nghiệm thu.
4. Phần giới thiệu nêu lợi ích giảm 80% thời gian, phần mục tiêu nêu 70%; cần thống nhất giá trị, baseline và phương pháp đo.
5. Kết quả hiệu năng và an toàn AI được báo cáo như đã đạt, nhưng không kèm dữ liệu kiểm thử có thể kiểm tra trong repository; cần bổ sung test set, scripts, cấu hình môi trường, raw/summary results và cách tính.

## 12. Hướng phát triển trong tương lai của báo cáo

Đây là các hướng mở rộng được nêu ở phần tương lai, không phải tiêu chí MVP bắt buộc đã hoàn thành:

- Kết nối thiết bị IoT, máy CNC/PLC qua Modbus/OPC UA để tự đếm sản lượng và phát hiện sự cố/nhiệt độ thời gian thực.
- Chạy LLM nội bộ/on-premises/edge để giảm độ trễ mục tiêu dưới 1 giây và hạn chế dữ liệu đi ra cloud.
- Phát triển ứng dụng mobile React Native hoặc Flutter để công nhân quét QR máy, check-in và báo sự cố.

**Đối chiếu:** Chưa có triển khai IoT, giao thức công nghiệp, AI edge hoặc native mobile trong repository hiện tại.

## 13. Ưu tiên khoảng cách so với code hiện tại

1. **Quyền riêng tư AI:** Nâng regex thành DLP/NER được đánh giá; bổ sung bộ test cho PII không gắn nhãn; không tuyên bố masking 100% khi chưa chứng minh.
2. **Nghiệp vụ còn thiếu:** Duyệt đơn, tiến độ %, tiêu hao BOM/kho, quy trình KCS/khắc phục, bảo trì và hiệu suất máy.
3. **AI safety/evidence:** Chạy 3 vòng prompt/model trên dataset xác định, red-team test set và review chuyên gia; đo jailbreak thay vì suy luận từ vài ví dụ.
4. **Tính toàn vẹn dữ liệu:** Chuyển bootstrap SQL sang Alembic có revision, backup/restore và thử nghiệm rollback/upgrade trên bản sao.
5. **Chứng minh chất lượng:** Full E2E browser, concurrency test lịch, load 50–100 user, latency benchmark, tablet tests; mọi chỉ tiêu cần raw result và phương pháp đo.
6. **Triển khai:** TLS/secret rotation, session/token revocation, least-privilege DB và quy trình deployment phù hợp; Docker Compose không dùng trong lần hoàn thiện này theo yêu cầu.
