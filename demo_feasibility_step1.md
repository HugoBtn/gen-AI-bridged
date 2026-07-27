# Demo Feasibility Assessment – Step 1: Bridge AI Interface

## 1. Mục tiêu của demo

Mục tiêu của phase 1 không phải là xây dựng sản phẩm hoàn chỉnh, mà là chứng minh được rằng:

1. AI có thể nhận câu hỏi bằng ngôn ngữ tự nhiên.
2. AI có thể xác định hệ thống dữ liệu phù hợp để truy vấn.
3. AI có thể gọi API/connector để lấy dữ liệu thực từ những hệ thống có thể truy cập.
4. AI có thể tổng hợp dữ liệu đa nguồn thành một câu trả lời thống nhất.
5. Khách hàng có thể hình dung rõ khả năng triển khai trong môi trường của họ.

---

## 2. Định nghĩa phạm vi demo phù hợp cho nghiên cứu thị trường

### 2.1. Demo nên tập trung vào chức năng nào?

Nên chọn các chức năng có thể biểu diễn rõ ràng trong 15–20 phút, đồng thời dễ hiểu với khách hàng:

- Chức năng 1: Trả lời một câu hỏi đa nguồn bằng ngôn ngữ tự nhiên.
- Chức năng 2: Truy vấn và so khớp dữ liệu giữa Salesforce và Sansan.
- Chức năng 3: Tổng hợp thông tin về customer/project/owner/trạng thái trong một câu trả lời duy nhất.
- Chức năng 4: Trình bày cách AI “ghi chú nguồn dữ liệu” để khách hàng tin vào câu trả lời.

### 2.2. Demo không nên quá rộng ở phase 1

Phase 1 không cần demo toàn bộ nền tảng SaaS. Nên tránh:

- Giới thiệu toàn bộ hệ thống kiểm soát truy cập chi tiết.
- Hiển thị mọi hệ thống nội bộ trong cùng một demo.
- Đề cập tới các tính năng hậu cần như billing, SSO, audit, role hierarchy phức tạp quá sớm.

> Gợi ý: demo nên chỉ chứng minh “AI có thể đi qua nhiều nguồn dữ liệu và trả lời như một trợ lý thông minh”.

---

## 3. Ma trận thẩm định tính khả thi theo chức năng

### Chức năng A: Chat UI nhận câu hỏi tự nhiên

- Tính khả thi: Cao
- Phạm vi demo: Một hộp chat đơn giản, nhập câu hỏi như: “Hãy cho tôi biết thông tin khách hàng A và trạng thái dự án liên quan”.
- Điều kiện tiên quyết để triển khai sản phẩm:
  - Có UI web/chat chính thức.
  - Có prompt template rõ ràng.
  - Có cơ chế ghi log và theo dõi câu hỏi.
- Ràng buộc:
  - Câu hỏi cần phải được chuẩn hóa theo intent.
  - Những câu hỏi quá mơ hồ có thể cần hỏi bổ sung.
- Khả năng mở rộng cho khách hàng khác: Cao

### Chức năng B: AI xác định hệ thống cần truy vấn

- Tính khả thi: Cao nếu có mapping intent → source system.
- Phạm vi demo: Với câu hỏi ví dụ, AI xác định cần truy vấn Salesforce, Sansan, hoặc internal project system.
- Điều kiện tiên quyết:
  - Có danh mục intent và mapping với source system.
  - Có metadata về schema dữ liệu hoặc API endpoint.
- Ràng buộc:
  - Nếu không có schema rõ ràng, AI có thể nhầm hệ thống cần truy vấn.
  - Với intent phức tạp, cần function calling / tool routing rõ ràng.
- Khả năng mở rộng cho khách hàng khác: Cao nếu thiết kế orchestration layer đúng.

### Chức năng C: Kết nối Salesforce sandbox

- Tính khả thi: Cao
- Phạm vi demo:
  - Truy vấn Account/Contact/Opportunity.
  - Lấy thông tin khách hàng, người liên hệ, vòng đời deal.
  - Hiển thị kết quả trên UI hoặc trong response.
- Điều kiện tiên quyết:
  - Có Salesforce sandbox hoặc test org.
  - Có API access credential.
  - Có dữ liệu mẫu đủ để demo.
- Ràng buộc:
  - API rate limit.
  - Quyền truy cập theo role và field-level security.
  - Một số dữ liệu cần xử lý thêm để làm sạch cho demo.
- Khả năng mở rộng cho khách hàng khác: Rất cao

### Chức năng D: Kết nối Sansan sandbox

- Tính khả thi: Cao nếu Sansan cung cấp API hoặc được hỗ trợ qua connector.
- Phạm vi demo:
  - Truy vấn thông tin công ty, nhân sự liên quan, dữ liệu đối tác.
  - So sánh với Salesforce để xác minh dữ liệu.
- Điều kiện tiên quyết:
  - Có sandbox/tenant thử nghiệm.
  - Có API contract hoặc sample data.
  - Có quy định về dữ liệu được phép dùng cho demo.
- Ràng buộc:
  - Nhiều hệ thống từ bên thứ ba có thể giới hạn API hoặc thiếu sandbox.
  - Tần suất truy vấn cần được kiểm soát.
- Khả năng mở rộng cho khách hàng khác: Trung bình đến cao

### Chức năng E: Kết nối hệ thống quản lý dự án nội bộ

- Tính khả thi: Cao nếu hệ thống có API và dữ liệu chuẩn hóa.
- Phạm vi demo:
  - Xác định project status, timeline, assignee, milestones.
  - Nối với dữ liệu customer từ Salesforce/Sansan.
- Điều kiện tiên quyết:
  - Có API endpoint cho project query.
  - Có định nghĩa quyền truy cập theo user/project.
  - Có dữ liệu mẫu với ít nhất 1–2 project case.
- Ràng buộc:
  - Nếu hệ thống nội bộ không có API hoặc cấu trúc dữ liệu không đồng nhất, khả năng demo sẽ giảm.
- Khả năng mở rộng cho khách hàng khác: Cao

### Chức năng F: Hợp nhất và tổng hợp dữ liệu từ nhiều nguồn

- Tính khả thi: Trung bình đến cao
- Phạm vi demo:
  - Câu hỏi: “Thông tin khách hàng X gồm mối quan hệ, project hiện tại, người phụ trách nào, liệu có công ty liên quan với Sansan không?”
  - AI trả lời bằng một câu trả lời duy nhất, kèm source reference.
- Điều kiện tiên quyết:
  - Có mapping định nghĩa rõ các entity chính (customer, contact, project, owner).
  - Có prompt orchestration và output schema rõ ràng.
- Ràng buộc:
  - Cần kiểm soát hallucination bằng source grounding.
  - Nếu hệ thống thiếu identifier chung, AI sẽ khó cross-link dữ liệu.
- Khả năng mở rộng cho khách hàng khác: Cao nếu chuẩn hóa dữ liệu trước.

### Chức năng G: Authorization / Permission enforcement

- Tính khả thi: Cao nhưng cần phát triển nghiêm ngặt
- Phạm vi demo:
  - Hiển thị rằng một user chỉ thấy dữ liệu họ được phép xem.
  - Ví dụ: nhân viên A không thấy data của nhân viên B.
- Điều kiện tiên quyết:
  - Có identity mapping và role-based access.
  - Có policy kiểm soát ở từng source system.
- Ràng buộc:
  - Không thể “bypass” quyền ở trung gian AI.
  - Nếu không có RBAC/ABAC chuẩn, AI bridge không thể tự động hóa quyền truy cập.
- Khả năng mở rộng cho khách hàng khác: Rất cao

### Chức năng H: Data freshness / realtime hoặc periodic sync

- Tính khả thi: Trung bình
- Phạm vi demo:
  - Có thể demo data freshness khi query live hoặc có cache theo thời gian thực.
- Điều kiện tiên quyết:
  - Quyết định chính sách: realtime, near realtime, hoặc polling định kỳ.
  - Có SLA cho từng hệ thống.
- Ràng buộc:
  - Một số hệ thống không hỗ trợ realtime.
  - Nếu dùng live query, cần kiểm soát latency và rate limit.
- Khả năng mở rộng cho khách hàng khác: Trung bình

### Chức năng I: Security / token / logging / audit

- Tính khả việt: Cao
- Phạm vi demo:
  - Hiển thị cách token được lưu an toàn, request được log, và có audit trail.
- Điều kiện tiên quyết:
  - Cấu hình secret management.
  - Có logging và trace ID cho mỗi request.
- Ràng buộc:
  - Không lưu trữ dữ liệu nhạy cảm dài hạn nếu không cần thiết.
  - Cần tuân thủ chính sách bảo mật của khách hàng.
- Khả năng mở rộng cho khách hàng khác: Rất cao

---

## 4. Demo case đề nghị cho khách hàng trong nghiên cứu thị trường

### Demo case 1: “Tìm thông tin khách hàng và trạng thái dự án”

Câu hỏi mẫu:

- “Cho tôi biết thông tin công ty ABC, ai là người liên hệ chính, và dự án hiện tại đang ở giai đoạn nào?”

Kết quả kỳ vọng:

- AI truy vấn Salesforce để lấy thông tin customer và contacts.
- AI truy vấn internal project system để lấy trạng thái dự án.
- AI trả lời bằng 1 câu trả lời, cộng với nguồn dữ liệu được trích dẫn.

### Demo case 2: “Kiểm tra dữ liệu giữa CRM và công ty đối tác”

Câu hỏi mẫu:

- “So sánh thông tin khách hàng ABC trong Salesforce và Sansan để xác định sự không nhất quán.”

Kết quả kỳ vọng:

- AI gọi cả Salesforce và Sansan.
- AI phân tích độ khớp dữ liệu.
- AI trả về các điểm không khớp và gợi ý cảnh báo.

### Demo case 3: “Tạo một brief nhanh cho account owner”

Câu hỏi mẫu:

- “Hãy tóm tắt nhanh tình hình khách hàng XYZ: thông tin liên hệ, deal đang chạy, project trạng thái, người phụ trách.”

Kết quả kỳ vọng:

- AI tổng hợp từ nhiều nguồn thành một brief kết quả.
- Khách hàng dễ hình dung giá trị thực tiễn của AI bridge.

---

## 5. Điều kiện tiên quyết để triển khai sản phẩm

### 5.1. Điều kiện kỹ thuật

- Có API hoặc connector cho từng source system.
- Có sandbox/test tenant cho Salesforce, Sansan, và ít nhất 1 hệ thống nội bộ.
- Có định danh chung giữa các hệ thống để cross-link dữ liệu.
- Có role-based access control và user identity mapping.
- Có data governance/bảo mật rõ ràng.

### 5.2. Điều kiện về dữ liệu

- Dữ liệu demo cần có cấu trúc rõ và phù hợp để AI truy vấn.
- Nên chuẩn hóa tên trường và entity để AI không cần đoán.
- Cần ít nhất 1 bộ dữ liệu thực tế hoặc dữ liệu representative để làm chứng minh.

### 5.3. Điều kiện vận hành

- Nên xác định SLA cho API response time.
- Nên quy định source system nào sử dụng live query, source system nào dùng poll.
- Nên có cơ chế giới hạn request / rate limit và retry.

---

## 6. Ràng buộc và điều kiện không thể hỗ trợ ở phase 1

### 6.1. Không thể hỗ trợ nếu:

- Source system không có API hoặc không cho phép tổ chức ngoài truy cập.
- Không có sandbox/test environment cho Salesforce/Sansan.
- Không có dữ liệu truy cập được hoặc dữ liệu bị phân mảnh quá mức.
- Không thể xác định quyền truy cập theo user.
- Không có identifier thống nhất giữa các hệ thống.

### 6.2. Những gì phase 1 không nên cam kết

- Không nên cam kết “AI sẽ trả lời chính xác 100% mọi câu hỏi”.
- Không nên cam kết “tự động đồng bộ dữ liệu realtime cho mọi hệ thống”.
- Không nên cam kết “mọi khách hàng đều dùng được ngay” khi chưa có yếu tố định nghĩa nguồn dữ liệu và quyền truy cập.

---

## 7. Khả năng mở rộng và áp dụng cho khách hàng khác

### 7.1. Khả năng mở rộng

Khả năng mở rộng của solution phụ thuộc vào 3 yếu tố:

1. Connector layer có thể thêm mới source system một cách chuẩn.
2. Orchestration layer có thể xác định intent và routing đúng.
3. Authorization layer tuân thủ quyền của từng hệ thống.

### 7.2. Có thể áp dụng cho nhiều khách hàng khác không?

- Có thể, nhưng không phải “với mọi công ty”.
- Điều kiện để mở rộng là khách hàng phải đáp ứng:
  - Có ít nhất 1–2 source system có API.
  - Có dữ liệu liên quan đủ cho demo.
  - Có quy định về bảo mật và quyền truy cập rõ ràng.
  - Có sẵn một môi trường sandbox/test để triển khai PoC.

> Kết luận: solution có thể được triển khai theo mô hình “customer-specific connector + shared AI orchestration layer”, thay vì một giải pháp universal cho mọi doanh nghiệp.

---

## 8. Khuyến nghị triển khai cho phase 1

### Ưu tiên triển khai demo

1. Salesforce sandbox connector
2. Sansan sandbox connector
3. Internal project system connector
4. Unified AI response with source grounding
5. Permission-aware response policy

### Ưu tiên không nên đặt vào phase 1

- Full production security hardening
- Complex multi-agent workflow
- Real-time sync toàn bộ hệ thống
- SaaS billing, multi-tenant governance, enterprise admin portal

---

## 9. Kết luận ngắn gọn cho khách hàng

Nếu khách hàng cung cấp:

- sandbox/test tenant cho Salesforce và Sansan,
- ít nhất một hệ thống nội bộ có API,
- quyền truy cập dữ liệu mẫu,
- và một định nghĩa rõ về phạm vi quyền xem,

thì phase 1 hoàn toàn có thể chứng minh tính khả thi bằng một demo thực tế, nơi AI có thể nhận câu hỏi bằng ngôn ngữ tự nhiên, truy vấn nhiều hệ thống, và trả về một câu trả lời thống nhất.
