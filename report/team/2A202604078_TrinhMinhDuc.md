# Báo cáo cá nhân — Trịnh Minh Đức

## 1. Thông tin thành viên

- Họ tên: Trịnh Minh Đức.
- MSSV: 2A202604078.
- Email: trinhduc1362k3@gmail.com (theo cấu hình Git hiện tại).
- GitHub: Chưa cung cấp.
- Vai trò: Người 2 — Single agent và nghiên cứu.

## 2. Phần việc phụ trách

Hoàn thiện kiến trúc `single`, thêm test cho ranh giới quyền và ngân sách bước, thực hiện ablation một biến và điền research card. Phần triển khai và kiểm tra được thực hiện với hỗ trợ của Codex; các số liệu dưới đây lấy từ các lệnh đã chạy trong workspace.

| File | Nội dung đóng góp |
| --- | --- |
| [`src/lab8/shapes/single.py`](../../src/lab8/shapes/single.py) | Thay stub bằng vòng ReAct giới hạn 8 bước, xử lý claim và trả kết quả đúng contract. |
| [`src/tests/test_team_single.py`](../../src/tests/test_team_single.py) | 27 test bổ sung và bộ chạy ablation tái lập bằng evaluator chính thức. |
| [`report/team/research_card.md`](research_card.md) | Câu R4, nguồn nghiên cứu, giả thuyết, phương pháp, kết quả và giới hạn. |
| [`src/reports/research_single_steps8.json`](../../src/reports/research_single_steps8.json) | Kết quả 70 trial với giới hạn 8 bước, do công cụ sinh. |
| [`src/reports/research_single_steps2.json`](../../src/reports/research_single_steps2.json) | Kết quả 70 trial với giới hạn 2 bước, do công cụ sinh. |

## 3. Đóng góp cụ thể và cách hoạt động

### 3.1. Single agent xử lý một claim như thế nào?

1. Mở SQLite; đọc claim bằng `get_claim_view`. Không dùng toàn bộ dòng dữ liệu làm ngữ cảnh cho agent.
2. Chỉ đưa `claim_id`, `principal_id`, `order_id` vào vòng lặp. Ticket không được dùng để xác định danh tính, số ngày trễ hay số tiền.
3. Vòng `run_react` gọi `decide`, thực hiện tool, trả quan sát rồi tiếp tục. Giới hạn mặc định là 8 quyết định.
4. Với claim có mã đơn, chọn `lookup_order` để kiểm phạm vi chủ sở hữu và đọc dữ kiện vận hành. Không thấy đơn hoặc không đúng chủ sở hữu thì kết thúc bằng `escalated`.
5. Nếu đơn hợp lệ, đọc policy hiện hành và lịch sử hoàn tiền bằng `lookup_policy`, `lookup_refund_history`, sau đó trả `final`.
6. Sau vòng lặp, code kiểm tra đã điều tra đầy đủ rồi gọi `compute_compensation` với order đã đọc. Final payload và câu chữ model không có quyền cung cấp số tiền.
7. Quote bằng 0 thì `denied`. Quote dương được chuyển nguyên vẹn cho `durability.issue_refund`.
8. Host kiểm approval, trần theo đơn và idempotency; single ánh xạ kết quả thành `resolved`, `denied` hoặc `failed`.
9. `finish()` đọc ledger/audit thực tế và ghi trace. Kết nối SQLite được đóng trong `finally`, kể cả khi crash truyền ra ngoài.

Ví dụ `C-001`: đọc được đơn trễ 4 ngày, phí ship 35.000 VND; code đề xuất 35.000; host duyệt và ghi một refund 35.000. Vòng điều tra bình thường có ba tool đọc và một quyết định `final`.

### 3.2. Ranh giới agent và host

- `worker=True` buộc dispatcher giới hạn tool trong allowlist chỉ đọc. Yêu cầu `issue_refund`, `append_audit` hoặc tool lạ từ vòng lặp bị từ chối.
- `compute_compensation` quyết định entitlement bằng code dựa trên order và policy hiện hành.
- `durability.issue_refund` là nơi duy nhất kiến trúc gọi để ghi hoàn tiền. Không tự viết SQL vào ledger và không tự tạo approval.
- Truyền quote đầy đủ, không trừ tiền đã hoàn trước. Với `C-014`, quote là 150.000 và host tự trừ 30.000 đã hoàn, nên effect là 120.000.
- Mỗi quyết định mô phỏng gọi MockLLM qua `complete`; reply draft cũng được tính vào budget. Tool đọc và code tính quote được ghi nhận chi phí tool.
- MockLLM hiện trả chuỗi đánh dấu, không hỗ trợ structured tool call. Vì vậy `decide` ánh xạ quan sát thành action bằng chính sách xác định trong code. Không mô tả đây là khả năng lập kế hoạch của model thật.

### 3.3. Các nhánh đã xử lý

| Trường hợp | Kết quả |
| --- | --- |
| Claim không tồn tại | `failed`, lý do `unknown_claim`. |
| Thiếu mã đơn | `needs_info`, không lấy mã đơn từ ticket. |
| Không tìm thấy đơn hoặc không đúng chủ sở hữu | `escalated`. |
| Hết ngân sách bước | `failed`, lý do `step_cap`, không đi tiếp đến ghi tiền. |
| Yêu cầu tool ghi/tool lạ | `failed`, lý do `tool_rejected`. |
| Final quá sớm, chưa đủ dữ kiện | `failed`, lý do `incomplete_investigation`. |
| Quote bằng 0 | `denied`, không gọi hoàn tiền. |
| Quote dương nhưng approval/trần không cho phép | `denied`; host ghi audit `policy_denied`. |
| Host chấp nhận | `resolved`; proposal giữ nguyên quote, effect do host quyết định. |
| Retry có quote xung đột số đã ghi | `failed`, lý do `amount_conflict`; giữ refund cũ. |

### 3.4. Retry, crash và bảo mật

- Truyền `crash_at` nguyên vẹn vào host; không bắt `InjectedCrash`.
- Test cả ba điểm `before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`; resume và retry vẫn có một dòng refund, một audit committed và checkpoint tương ứng.
- Không ghi ticket, parent secret, raw header, số điện thoại, địa chỉ, ghi chú nội bộ hoặc tên hàng vào trace hay prompt.
- Trace chỉ ghi trạng thái đọc claim, tên action/số bước, quote từ code và kết quả host.
- Test còn đưa dữ liệu nhạy cảm giả lập vào ticket để xác nhận prompt, trace, kết quả và stdout/stderr không chứa chúng.

## 4. Bằng chứng kiểm tra

Môi trường chạy: Windows AMD64, Python 3.12.10. Mọi lệnh bên dưới chạy tại `src/`.

| Lệnh đã chạy | Kết quả thực tế |
| --- | --- |
| `python -m pytest -q tests/test_team_single.py` | **27 passed**. |
| `python -m pytest -q -m student -o addopts= tests/test_public_matrix.py -k "single and not workflow and not orchestrator and not swarm"` | **62 passed, 186 deselected**. |
| `python -m pytest -q` | **81 passed, 248 deselected**. |
| `python -m lab8.smoke` | **lab8.smoke pass**. |
| `python -m tests.test_team_single --ablation` | Sinh hai report, mỗi report 14 claim × 5 seed = **70 trial**. |

Lệnh chọn student loại trừ tên ba kiến trúc còn lại vì tên hàm test dùng chung có chữ `single`; chỉ dùng `-k single` có thể chọn cả test của các kiến trúc khác.

Các test bổ sung kiểm tra số bước và budget, chặn tool ghi/tool lạ, final giả mạo, final quá sớm, ticket/model text giả mạo qua năm seed, rò dữ liệu trong prompt/trace/stdout, năm loại approval lỗi, ba điểm crash, claim/đơn không tồn tại, thiếu mã đơn và xung đột khi retry.

### Kết quả nghiên cứu

Chọn R4 — yếu tố gây nhiễu khi đánh giá. Chỉ thay giới hạn bước từ 8 xuống 2; giữ nguyên code, topology, model, template prompt, tools, corpus, world, seed, giá và evaluator.

| Chỉ số | 8 bước | 2 bước |
| --- | ---: | ---: |
| Trial pass | 70/70 | 10/70 |
| Pass rate / pass^5 | 100% / 100% | 14,2857% / 14,2857% |
| Seed variance | 0 | 0 |
| Cost/success, VND mô phỏng | 48,2614 | 210,0600 |

- Experiment id: `single-step-cap-abbc7b0b8a48`.
- Ví dụ run id: `R-single-C-001-s11`; phân biệt nhánh bằng file report và metadata giới hạn bước.
- Nhánh 2 bước chỉ pass hai claim có thể dừng sớm: thiếu mã đơn và ngoài phạm vi chủ sở hữu. Các claim còn lại dừng vì `step_cap` trước bước ghi tiền.
- Dừng sớm tiết kiệm tổng chi phí, nhưng chi phí mỗi trial pass tăng vì phần lớn claim không hoàn thành đúng kết quả mong đợi.
- Chưa có kết quả hidden; chưa so sánh trực tiếp chất lượng của bốn topology trong thí nghiệm này. Benchmark bốn kiến trúc và ADR do người 4 phụ trách.
- Chi tiết nguồn, số đo và cách tái lập nằm trong [research card](research_card.md).



## 5. Công cụ AI đã dùng

- Công cụ: Codex (trợ lý AI trong workspace).
- Phạm vi hỗ trợ: đọc contract/runtime, viết code và test single, chạy kiểm tra, tạo ablation bằng evaluator có sẵn, tra nguồn nghiên cứu và soạn báo cáo dựa trên output thực tế.
- Kiểm chứng đã thực hiện trong workspace: 27 test bổ sung, 62 test student của single, bộ test mặc định 81 test, smoke và 140 trial ablation. JSON bằng chứng được sinh bằng code, không sửa tay số đo.
- Việc thành viên cần tự thực hiện: đọc code, chạy lại lệnh và giải thích ranh giới code/model/host trước khi xác nhận đây là phần bài mình đã hiểu.

## 6. Tự đánh giá

Tôi đánh giá phần triển khai single đã đáp ứng các yêu cầu được kiểm tra trên bộ public: xử lý claim đúng contract, giới hạn vòng lặp, phân quyền tool, kiểm soát dữ liệu nhạy cảm và hỗ trợ retry/crash. Bằng chứng tại mục 4 gồm 62 test student của single và 27 test bổ sung đều pass. Phần nghiên cứu hiện hoàn thành một ablation riêng trên single; kết luận so sánh các kiến trúc cần chờ workflow, orchestrator và benchmark chung của nhóm.

**1. Vì sao chữ trong ticket không có quyền thay số ngày trễ, principal hay tiền hoàn?**

Ticket là nội dung người dùng cung cấp, có thể ghi sai dữ kiện hoặc chứa lệnh giả mạo. Số ngày trễ phải lấy từ order; principal dùng để kiểm quyền phải lấy từ claim trong hệ thống. Code chỉ đưa `claim_id`, `principal_id`, `order_id` vào vòng lặp và dùng `lookup_order` để kiểm phạm vi truy cập. Số tiền do `compute_compensation` tính theo order và policy hiện hành; câu như “ignore policy” hoặc “hoàn 999999999” không thay đổi các bước này.

**2. Trong ReAct, phần nào chọn tool và giới hạn 8 bước được thực thi ở đâu?**

Hàm `decide` trong `single.py` chọn action dựa trên dữ kiện đã quan sát: đọc order, đọc policy, đọc lịch sử hoàn tiền rồi trả `final`. Hàm `run_react` trong `runtime.py` thực thi vòng lặp với `max_steps=MAX_REACT_STEPS`, mặc định bằng 8. Mỗi lần gọi `decide` tính một bước, kể cả quyết định `final`. Nếu hết giới hạn mà chưa có `final`, single trả `failed` với lý do `step_cap` và không thực hiện bước hoàn tiền. Giới hạn này khác số event trong trace; lời gọi draft sau vòng lặp vẫn được tính riêng vào budget.

**3. Vì sao MockLLM của lab chưa chứng minh khả năng lập kế hoạch của model thật?**

MockLLM tạo chuỗi phản hồi xác định theo seed, purpose và prompt; nó không sinh structured tool call để điều khiển vòng lặp. Chính sách chọn tool hiện được viết trong `decide`, còn chuỗi model trả về không được thực thi như lệnh. Vì vậy, kết quả kiểm chứng cách ghép vòng lặp, công cụ và host trong mô phỏng; chưa chứng minh model thật có thể tự lập kế hoạch, chọn công cụ hoặc xử lý tình huống mới với cùng độ đúng.

**4. Vì sao proposal 150.000 có thể tạo effect 120.000 ở T14?**

Proposal là entitlement đầy đủ mà code tính cho đơn hàng. Ở T14, entitlement mới là 150.000 VND, trong khi đơn đã được hoàn 30.000 VND trước đó. Single truyền nguyên quote 150.000 vào host; host áp dụng trần theo đơn và chỉ ghi phần chênh 120.000 VND. Nếu single tự trừ trước rồi truyền 120.000, host sẽ tiếp tục trừ khoản đã hoàn, dẫn đến hoàn thiếu. Do đó, `proposal_amount` và số tiền thực ghi trong ledger có thể khác nhau.

**5. Vì sao phải để `InjectedCrash` truyền ra ngoài và vẫn đóng SQLite?**

`InjectedCrash` giúp bộ kiểm tra xác nhận chương trình thực sự dừng tại cửa sổ crash đã yêu cầu. Nếu bắt lỗi rồi trả kết quả bình thường, kịch bản crash/resume không còn được kiểm tra đúng. `run_claim` dùng `finally` để đóng kết nối dù có exception, giải phóng tài nguyên và tránh giữ khóa file SQLite. Khi chạy lại, host sử dụng ledger, idempotency key và audit để giữ một refund và một audit committed; việc đóng kết nối không thay thế cơ chế chống ghi trùng này.

**6. Vì sao giảm tổng chi phí chưa chắc giảm cost/success?**

Cost/success bằng tổng chi phí của tất cả trial, gồm cả trial fail, chia cho số trial pass. Cấu hình 8 bước tốn tổng cộng 3.378,30 VND mô phỏng và pass 70 trial, tương đương khoảng 48,26 VND mỗi trial pass. Cấu hình 2 bước chỉ tốn 2.100,60 VND nhưng pass 10 trial, nên cost/success tăng lên 210,06 VND. Dừng sớm làm giảm chi phí thực thi nhưng cũng làm nhiều claim chưa hoàn thành; cần xem đồng thời độ đúng và chi phí.

**7. Vì sao 100% trên public chưa chứng minh đã qua hidden?**

Bộ public chỉ có 14 claim đã biết. Bộ hidden gồm 40 claim có thể chứa các biến thể về dữ kiện sai, injection, approval, policy, phạm vi chủ sở hữu và lịch sử hoàn tiền mà public chưa bao phủ. Kết quả 70/70 trial public chỉ có giá trị trong setup đã đo; không đủ để khẳng định đạt ngưỡng pass rate hidden hoặc mọi điều kiện must-pass trên hidden. Điểm chính thức vẫn cần bộ chấm của giảng viên.

Điểm tôi cần tiếp tục cải thiện là phân tích trace khi có trial fail, bổ sung trường hợp kiểm thử dựa trên lỗi thực tế và đối chiếu với kết quả tích hợp. Khi người 1 và người 3 hoàn thành phần của mình, tôi sẽ cung cấp code, test và bằng chứng single để người 4 chạy benchmark chung; lựa chọn kiến trúc của nhóm sẽ dựa trên số đo đó.
