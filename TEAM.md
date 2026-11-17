# Team

## Thông tin nhóm

- Tên nhóm: ichiban
- Lớp: L3A
- Repo nhóm: `K5-L3B-DAY08-ichiban-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: https://github.com/TADIZB/K5-L3B-DAY08-ichiban-FromWorkflowsToAgents, nhánh `main`, commit chấm `cfca584` (trùng `report/team/decision_adr.md`)

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Đặng Khắc Hoàng Minh | 2A202604082 | dangkhacm@gmail.com | Chưa cung cấp | Workflow, tích hợp và báo cáo nhóm |
|   2 | Trịnh Minh Đức | 2A202604078 | trinhduc1362k3@gmail.com | Chưa cung cấp | Single agent và nghiên cứu |
|   3 | Nguyễn Việt Hoàng | 2A202604104 | viethoangnv0810@gmail.com | viethoang126 | Orchestrator và bảo mật handoff |
|   4 | Trương Anh Đức | 2A202604096 | Chưa cung cấp | TADIZB | Kiểm thử tích hợp, benchmark, ADR và bonus B3 |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Người 1 — Đặng Khắc Hoàng Minh | Workflow, tích hợp và báo cáo nhóm | `d153a50` | `src/tests/test_team_workflow.py` (3 test; lúc commit chưa chạy được do thiếu pytest, chạy lại ngày 2026-11-17: 3 passed) |
| Người 2 — Trịnh Minh Đức | Single agent và nghiên cứu | `c6b4c99`, `984d09c` | `src/tests/test_team_single.py` (27 passed) |
| Người 3 — Nguyễn Việt Hoàng | Orchestrator và bảo mật handoff | `7f39a3a` | `src/tests/test_team_orchestrator.py` (72 passed) |
| Người 4 — Trương Anh Đức | Kiểm thử tích hợp, benchmark, ADR và bonus B3 | `87a16b2`, `a9dcff2`, `cfca584` | `src/tests/test_team_integration.py` (142 passed), `src/tests/test_bonus_swarm_verified.py` (72 passed) |

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
- Ba test workflow đã thêm; lúc commit chưa chạy được do môi trường thiếu `pytest`. Chạy lại trong venv ngày 2026-11-17: `python -m pytest -q tests/test_team_workflow.py` → 3 passed; workflow qua 62/62 test student.

## Người 2 — Trịnh Minh Đức (`2A202604078_TrinhMinhDuc.md`)

### Phần việc phụ trách

- Single agent ReAct tối đa 8 bước, model chỉ chọn tool đọc; research card R4 và ablation giới hạn bước.

### Đóng góp cụ thể

- Triển khai `src/lab8/shapes/single.py`; thêm `src/tests/test_team_single.py`; chạy ablation 8 bước so với 2 bước, sinh `src/reports/research_single_steps8.json` và `research_single_steps2.json`; điền `report/team/research_card.md`.

### Bằng chứng

- Commit `c6b4c99` (single + ablation), `984d09c` (báo cáo). 27 test bổ sung passed; single qua 62/62 test student; ablation 70/70 so với 10/70 trial pass.

## Người 3 — Nguyễn Việt Hoàng (`2A202604104_NguyenVietHoang.md`)

### Phần việc phụ trách

- Orchestrator và investigator chỉ đọc; handoff allowlist; trace không chứa secret/PII.

### Đóng góp cụ thể

- Triển khai `src/lab8/shapes/orchestrator.py` (handoff `facts={}`, `_assert_readonly`, `_GuardedTrace`); thêm `src/tests/test_team_orchestrator.py`.

### Bằng chứng

- Commit `7f39a3a`. 72 test bổ sung passed; orchestrator qua 62/62 test student; ba điểm crash/resume đúng.

## Người 4 — Trương Anh Đức (`2A202604096_TruongAnhDuc.md`)

### Phần việc phụ trách

- Test tích hợp cho ba shape; crash suite và benchmark chốt bài; ADR; bonus B3.

### Đóng góp cụ thể

- Thêm `src/tests/test_team_integration.py`; sinh `src/reports/crash.json`, `src/reports/benchmark.json`; phát hiện và sửa lỗi workflow chép ticket vào trace; điền `report/team/decision_adr.md`; làm bonus B3 (`src/bonus/`, `report/team/bonus_report.md`).

### Bằng chứng

- Commit `87a16b2`, `a9dcff2`, `cfca584`. 142 test tích hợp và 72 test bonus passed; crash 20/20; benchmark 4 shape × 14 claim × 5 seed.
