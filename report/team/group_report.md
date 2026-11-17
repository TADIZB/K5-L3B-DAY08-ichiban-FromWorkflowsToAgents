# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: Chưa được cung cấp.
- Thành viên: xem `TEAM.md`; thông tin cá nhân đang chờ nhóm bổ sung.
- Commit chốt (trùng `report/team/decision_adr.md`): Chưa chốt.

## 2. Mục tiêu và cách tiếp cận

Nhóm triển khai cùng một quy trình hoàn claim qua bốn shape để so sánh workflow, single agent, orchestrator và swarm trên cùng dữ liệu. Theo `PHAN_CONG.md`, Người 1 phụ trách workflow, tích hợp và báo cáo nhóm; các phần của thành viên còn lại cần được tổng hợp từ bằng chứng thực tế trước khi nộp.

## 3. Giải pháp

Workflow chạy theo trình tự xác định: đọc claim bằng `get_claim_view`, kiểm tra quyền xem order bằng `lookup_order`, tính quote bằng `compute_compensation` từ dữ kiện order, rồi chuyển nguyên quote cho host `issue_refund`. Model không quyết định tiền và workflow không tự ghi ledger. Nhánh thiếu order id, không thấy order, quote bằng 0, host từ chối và thành công đều trả `RunResult` qua `finish` và ghi trace riêng. Crash được chuyển cho host và truyền ra ngoài để kiểm tra resume.

Chi tiết single agent, orchestrator, handoff và trace toàn hệ thống cần được bổ sung từ các thành viên phụ trách sau khi tích hợp.

## 4. Kết quả

Chưa có benchmark/crash report được sinh trong workspace, nên chưa ghi số liệu so sánh. Sau khi Người 4 tạo `src/reports/benchmark.json` và `src/reports/crash.json`, điền bảng kết quả, run id, commit hash và đối chiếu với ADR.

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

Các rủi ro chính của workflow là ticket có thể đưa dữ kiện trễ sai lệch so với order, trace có thể vô tình chứa thông tin nhạy cảm, và host áp dụng cap theo đơn. Workflow dùng dữ kiện từ order, ghi trace các trường allowlist từ read tools và gửi quote đầy đủ để host tự áp dụng cap.

## 6. Tổng hợp đóng góp

Đóng góp cụ thể của từng thành viên sẽ được tổng hợp từ `TEAM.md`, lịch sử commit và báo cáo cá nhân sau khi nhóm cung cấp tên/MSSV và bằng chứng commit/test. Hiện báo cáo ghi nhận phần việc Người 1 theo `PHAN_CONG.md`.

## 7. Hạn chế và hướng cải thiện

Các shape được kiểm thử trên dữ liệu public và MockLLM; kết quả không đại diện đầy đủ cho model hay dữ liệu sản xuất. Kết luận kiến trúc cần giới hạn trong corpus, seed, bảng giá và cấu hình đã đo; mục này sẽ được cập nhật cùng số liệu benchmark.

## 8. Tài liệu tham khảo

`README.md`, `docs/business_rules.md`, `docs/contracts.md`, `docs/architecture.md` và `PHAN_CONG.md`.
