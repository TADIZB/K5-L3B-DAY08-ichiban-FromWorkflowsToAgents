# Team

## Thông tin nhóm

- Tên nhóm:
- Lớp: L3A
- Repo nhóm: `K5-L3A-DAY08-TenNhom-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt:

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Đặng Khắc Hoàng Minh | 2A202604082 | dangkhacm@gmail.com | Chưa cung cấp | Workflow, tích hợp và báo cáo nhóm |
|   2 |        |      |       |        |         |
|   4 | Trương Anh Đức | 2A202604096 | Chưa cung cấp | TADIZB | Kiểm thử tích hợp, benchmark và ADR |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Người 1 — Đặng Khắc Hoàng Minh | Workflow, tích hợp và báo cáo nhóm | `d153a50` | `src/tests/test_team_workflow.py` (3 test; chưa chạy tại thời điểm commit do thiếu pytest và không tải được dependency) |
| Người 4 — Trương Anh Đức | Kiểm thử tích hợp, benchmark và ADR | `87a16b2`, `a9dcff2` | `src/tests/test_team_integration.py` (đã thêm, 142 passed) |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## Người 1 — Đặng Khắc Hoàng Minh (`2A202604082_DangKhacHoangMinh.md`)

### Phần việc phụ trách

- Workflow cố định: đọc claim/order qua read tools, tính quote bằng dữ kiện order và gọi host với quote đầy đủ.

### Đóng góp cụ thể

- Triển khai `src/lab8/shapes/workflow.py` và thêm test cho ticket/order lệch dữ kiện, cap theo order, trace an toàn, crash/resume.

### Bằng chứng

- Commit `d153a50` triển khai workflow, thêm `src/tests/test_team_workflow.py` và cập nhật báo cáo nhóm.
- Ba test workflow đã thêm; chưa chạy tại thời điểm commit do môi trường thiếu `pytest` và không tải được dependency.
