# Báo cáo cá nhân — Đặng Khắc Hoàng Minh

## 1. Thông tin thành viên

- Họ tên: Đặng Khắc Hoàng Minh
- MSSV: 2A202604082
- Email: dangkhacm@gmail.com (theo cấu hình Git)
- GitHub: Chưa cung cấp
- Vai trò: Người 1 — Workflow, tích hợp và báo cáo nhóm

## 2. Phần việc phụ trách

Theo `PHAN_CONG.md`, tôi phụ trách shape workflow cố định, test riêng cho workflow, quản lý tích hợp và tổng hợp thông tin nhóm.

| File | Nội dung |
| --- | --- |
| [`src/lab8/shapes/workflow.py`](../../src/lab8/shapes/workflow.py) | Triển khai luồng đọc claim/order, tính quote từ order và gọi host hoàn tiền. |
| [`src/tests/test_team_workflow.py`](../../src/tests/test_team_workflow.py) | Thêm test về ticket mâu thuẫn với dữ kiện order, cap hoàn tiền theo đơn, trace an toàn và crash/resume. |
| [`TEAM.md`](../../TEAM.md), [`report/team/group_report.md`](group_report.md) | Cập nhật thông tin đóng góp và tổng hợp phần workflow vào báo cáo nhóm. |

## 3. Đóng góp cụ thể

### 3.1. Commit

| Commit | Nội dung |
| --- | --- |
| `d153a50` | Triển khai workflow xác định, thêm ba test workflow, cập nhật `TEAM.md` và báo cáo nhóm. |

### 3.2. Thiết kế workflow

Workflow gọi `get_claim_view` để lấy claim, yêu cầu `lookup_order` xác nhận order thuộc đúng principal, rồi tính mức bồi thường bằng `compute_compensation` từ dữ kiện order. Nội dung ticket không quyết định số ngày trễ hay số tiền. Nếu quote dương, workflow chuyển nguyên quote cho `issue_refund`; host chịu trách nhiệm kiểm tra approval, áp dụng cap theo order và ghi ledger/audit. Workflow không tự ghi ledger.

Các nhánh claim không tồn tại, thiếu order id, order không hiển thị, quote bằng 0, host từ chối và thành công được trả qua `finish`. Workflow chuyển `crash_at` cho host, để `InjectedCrash` truyền ra ngoài và đóng kết nối SQLite trong `finally`.

### 3.3. Test đã thêm

- `test_workflow_uses_order_facts_instead_of_ticket_and_writes_safe_trace`: kiểm tra ticket khai trễ năm ngày không làm thay đổi quyết định dựa trên order, đồng thời kiểm tra trace không chứa secret hoặc các trường nhạy cảm đã nêu.
- `test_workflow_passes_full_quote_to_host_for_per_order_cap`: kiểm tra quote 150.000 VND được chuyển nguyên cho host và effect theo cap còn 120.000 VND.
- `test_workflow_forwards_crash_and_retry_resumes_once`: kiểm tra crash được truyền ra ngoài và resume chỉ tạo một refund cùng một audit `refund_committed`.

## 4. Bằng chứng

- Commit triển khai: `d153a50` (`Implement deterministic claim workflow`).
- Test bổ sung: [`src/tests/test_team_workflow.py`](../../src/tests/test_team_workflow.py).
- Tại thời điểm commit, ba test mới chưa được chạy vì môi trường thiếu `pytest` và việc tải dependency bị chặn bởi kết nối mạng. Vì vậy, báo cáo không ghi nhận các test này là đã pass.
- Đã kiểm tra diff trước commit bằng `git diff --check`; lệnh không báo lỗi whitespace.

## 5. Công cụ AI đã dùng

- Công cụ: Codex trong workspace.
- Phạm vi hỗ trợ: triển khai workflow, soạn test bổ sung và chuẩn bị nội dung báo cáo dựa trên phân công, source code và lịch sử Git.
- Tự kiểm tra: đối chiếu thay đổi với contract trong docstring workflow, xem diff và commit, kiểm tra các file test/báo cáo. Các test mới chưa được chạy tại thời điểm commit do thiếu `pytest` và không tải được dependency; cần chạy lại trong môi trường có dependency trước khi xác nhận kết quả test.

## 6. Tự đánh giá

Phần workflow đã đi theo ranh giới trách nhiệm của lab: code lấy dữ kiện có thẩm quyền và tính quote, còn host kiểm tra policy và thực hiện ghi tiền. Bộ test bổ sung tập trung vào ba rủi ro thực tế là ticket sai lệch, cap theo order và tính an toàn khi crash/resume.

Hạn chế hiện tại là chưa xác nhận trực tiếp kết quả chạy của ba test bổ sung trong môi trường này. Bước tiếp theo là chạy test workflow và ma trận student khi `pytest` khả dụng, sau đó cập nhật kết quả thực tế vào báo cáo nhóm nếu có thay đổi.
