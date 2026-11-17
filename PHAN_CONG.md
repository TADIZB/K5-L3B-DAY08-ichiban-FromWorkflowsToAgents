# Phân công dự án cho nhóm 4 người

Dự án: **Lab 8 — From Workflows to Agents (LogiX-VN)**.

Repo có ba kiến trúc cần triển khai: `workflow`, `single`, `orchestrator`. Kiến trúc `swarm` đã có sẵn để đối chứng. Nhóm chia thành ba người phát triển và một người kiểm thử, đánh giá; phân bổ thêm báo cáo và nghiên cứu để mỗi người có khối lượng dự kiến khoảng 25% tổng công sức.

Nguyên tắc: **mỗi file có một người phụ trách sửa; lỗi thuộc kiến trúc nào thì người phụ trách kiến trúc đó sửa**.

## 1. Bảng phân công

| Người | Vai trò | Công việc chính | File phụ trách |
| --- | --- | --- | --- |
| **Người 1** | Workflow, tích hợp và báo cáo nhóm | Viết quy trình cố định; quản lý merge; tổng hợp thông tin và báo cáo nhóm. | `src/lab8/shapes/workflow.py`; tạo `src/tests/test_team_workflow.py`; `TEAM.md`; `report/team/group_report.md`. |
| **Người 2** | Single agent và nghiên cứu | Viết vòng ReAct; thiết kế, chạy và phân tích một ablation; hoàn thiện research card. | `src/lab8/shapes/single.py`; tạo `src/tests/test_team_single.py`; `report/team/research_card.md`. |
| **Người 3** | Orchestrator và bảo mật handoff | Viết orchestrator và investigator chỉ đọc; bảo vệ secret, thông tin cá nhân và trace. | `src/lab8/shapes/orchestrator.py`; tạo `src/tests/test_team_orchestrator.py`. |
| **Người 4** | Kiểm thử tích hợp, benchmark và ADR | Viết test tích hợp; chạy kiểm tra chung, crash suite và benchmark; lập bằng chứng và quyết định kiến trúc. | Tạo `src/tests/test_team_integration.py`; sinh `src/reports/benchmark.json`, `src/reports/crash.json`; `report/team/decision_adr.md`. |

Workflow có độ phức tạp thấp hơn nên người 1 nhận thêm tích hợp và báo cáo. Người 2 nhận thêm nghiên cứu. Người 3 tập trung vào orchestrator và ranh giới bảo mật. Người 4 đóng góp kỹ thuật qua test tích hợp, đồng thời chịu trách nhiệm số liệu và bằng chứng.

## 2. Công việc và tiêu chí bàn giao từng người

### Người 1 — Workflow, tích hợp và báo cáo nhóm

- Đọc claim và order qua các công cụ có sẵn; xử lý đầy đủ các nhánh kết quả theo contract.
- Tính tiền bằng `compute_compensation`, dựa trên dữ kiện order; không tin số ngày trễ ghi trong ticket.
- Truyền quote đầy đủ vào `durability.issue_refund`; chuyển tiếp `crash_at` và để `InjectedCrash` truyền ra ngoài.
- Ghi trace đúng contract ở mọi nhánh trả kết quả; xử lý retry không tạo refund trùng.
- Thêm test riêng cho workflow, ưu tiên trường hợp ticket và order cung cấp dữ kiện khác nhau.
- Quản lý merge các nhánh đã bàn giao; tổng hợp `TEAM.md` và `group_report.md` từ bằng chứng của từng thành viên.

**Bàn giao:** workflow qua 62 test student có sẵn của kiến trúc này; test bổ sung chạy xanh; thông tin nhóm và báo cáo nhóm đầy đủ.

### Người 2 — Single agent và nghiên cứu

- Dùng `run_react` với tối đa 8 bước; quyết định của model chỉ chọn tool đọc.
- Sau vòng lặp, code tính quote và gọi host để hoàn tiền; ghi nhận model call và budget đúng quy định.
- Xử lý đầy đủ kết quả, trace, retry và crash theo contract.
- Thêm test riêng cho giới hạn bước và quyền gọi tool của single agent.
- Chọn một câu R1–R4 trong research card; thiết kế ablation chỉ thay đổi một biến, giữ cố định các yếu tố còn lại.
- Chạy ablation, lưu kết quả bằng công cụ và điền phương pháp, lệnh chạy, run id, số liệu cùng giới hạn kết luận.

**Bàn giao:** single qua 62 test student có sẵn của kiến trúc này; test bổ sung chạy xanh; research card có bằng chứng thực tế.

### Người 3 — Orchestrator và bảo mật handoff

- Tạo handoff qua `make_handoff`, chỉ chuyển các field trong allowlist.
- Dùng investigator chỉ có tool đọc; orchestrator chịu trách nhiệm tính quote và gọi host để hoàn tiền.
- Không chuyển parent context, secret, header thô hay toàn bộ claim/order sang investigator hoặc trace.
- Ghi trace từ handoff đã sanitize; xử lý đầy đủ kết quả, retry và crash.
- Thêm test riêng chứng minh handoff không mang secret và không cấp tool ghi.

**Bàn giao:** orchestrator qua 62 test student có sẵn của kiến trúc này; test bảo mật bổ sung chạy xanh; retry và crash/resume hoạt động đúng.

### Người 4 — Kiểm thử tích hợp, benchmark và ADR

- Chuẩn bị test tích hợp ngay khi người 1–3 bắt đầu viết các kiến trúc.
- Thêm test áp dụng cùng các bất biến cho cả ba kiến trúc, ưu tiên approval, retry và crash/resume. Kiểm tra trạng thái ledger và audit thực tế.
- Chạy bộ test chung và ma trận student; ghi rõ trường hợp lỗi, lệnh tái hiện và chuyển về đúng người phụ trách.
- Chạy crash suite và benchmark bốn kiến trúc trên cùng corpus, cùng năm seed và cùng bảng giá.
- Tạo các file JSON bằng công cụ của lab; không sửa tay kết quả.
- Điền ADR dựa trên số đo: kiến trúc được chọn, lý do, run id, commit hash, chi phí, độ ổn định và giới hạn kết luận.
- Tự kiểm trên `student_drop/` khi được giảng viên cung cấp; phân biệt kết quả tự kiểm với điểm hidden chính thức.

**Bàn giao:** bộ test chung và student xanh; crash suite đạt `20/20`; benchmark đủ bốn kiến trúc, ít nhất 10 claim và seed `11,22,33,44,55`; ADR khớp bằng chứng.

**Lưu ý:** crash suite `20/20` cần đi kèm kiểm tra T11–T12 của từng kiến trúc. Riêng kết quả crash suite chưa đủ để kết luận cả ba kiến trúc đã chuyển tiếp crash và resume đúng.

## 3. Quy tắc tránh chồng chéo

1. Mỗi người làm trên một nhánh riêng, ví dụ `feat/workflow`, `feat/single`, `feat/orchestrator`, `test/integration-eval`.
2. Chỉ sửa các file được giao. Nếu cần thay đổi file người khác phụ trách, thống nhất trước và để chủ file thực hiện.
3. Người 4 báo lỗi bằng test tái hiện và kết quả kiểm tra; chủ kiến trúc sửa code tương ứng.
4. Người 1 quản lý merge. Xung đột nội dung trong file kiến trúc được chuyển cho chủ file xử lý.
5. `group_report.md` chỉ do người 1 chỉnh sửa. Các thành viên cung cấp mô tả, khó khăn và bằng chứng qua báo cáo cá nhân để người 1 tổng hợp.
6. Người 4 tạo bộ số liệu benchmark/crash dùng để chốt bài. Người 2 chạy ablation ra file kết quả riêng, không ghi đè các file bằng chứng chốt.
7. Mỗi người tự tạo báo cáo `report/team/<MSSV>_<HoTen>.md` từ mẫu; giữ nguyên file mẫu `MSSV_HoTen.md`.
8. Mỗi người phải có commit kỹ thuật có nội dung và ít nhất một test tự thêm hoặc sửa. Chạy test có sẵn không thay thế yêu cầu này.
9. Cả nhóm giữ nguyên chữ ký `run_claim` và sử dụng host, công cụ, contract có sẵn. Không tạo thêm module dùng chung ngoài ba file kiến trúc để tránh phụ thuộc bị bỏ qua khi chấm hidden.
10. Giữ nguyên thước đo và host có sẵn, đặc biệt `metrics.py`, `durability.py`, `policy.py`, `config/`, `data/` và công cụ chấm. Không sửa tay JSON trong `src/reports/`.

## 4. Trình tự phối hợp

| Giai đoạn | Người 1 | Người 2 | Người 3 | Người 4 |
| --- | --- | --- | --- | --- |
| **CP1: Chuẩn bị** | Cùng nhóm chạy smoke/test nền; chốt phân công và cập nhật `TEAM.md`. | Đọc contract, runtime và chọn hướng nghiên cứu. | Đọc handoff, trace và quy tắc bảo mật. | Xác nhận trạng thái ban đầu, chuẩn bị checklist và test tích hợp. |
| **CP2–CP3: Phát triển song song** | Viết workflow và test riêng. | Viết single và test riêng; chốt phương pháp ablation. | Viết orchestrator và test riêng. | Viết test tích hợp và chuẩn bị khung ADR, quy trình đo. |
| **CP4: Tích hợp và an toàn** | Merge phần đã đạt yêu cầu; sửa lỗi workflow. | Sửa lỗi single. | Sửa lỗi orchestrator và handoff. | Chạy kiểm tra chung, crash suite; gửi lỗi về đúng chủ file. |
| **CP5: Đo và chốt bài** | Tổng hợp báo cáo nhóm, bảng đóng góp. | Chạy ablation, hoàn thiện research card. | Rà soát bảo mật lần cuối và cung cấp mô tả kỹ thuật. | Tạo benchmark/crash report và hoàn thiện ADR. |

Mỗi thành viên hoàn thiện báo cáo cá nhân và cung cấp commit/test làm bằng chứng trước khi chốt bài.

## 5. Lệnh kiểm tra và checklist bàn giao

Mọi lệnh dưới đây chạy trong thư mục `src/`.

Kiểm tra riêng từng kiến trúc; người phụ trách thay tên sau `-k` bằng `workflow`, `single` hoặc `orchestrator`:

```powershell
python -m pytest -q -m student -o addopts= -k workflow
```

Sau khi tích hợp:

```powershell
python -m pytest -q
python -m pytest -q -m student -o addopts=
python -m lab8.crash_test --count 20 --out reports/crash.json
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
```

Commit code và bằng chứng, lấy hash bằng `git rev-parse --short HEAD`, ghi hash cùng run id vào ADR rồi commit phần tài liệu. Cuối cùng kiểm tra:

```powershell
python -m lab8.check_submission
```

- [ ] Ba kiến trúc được triển khai đầy đủ, mỗi kiến trúc qua 62 test student có sẵn.
- [ ] Test bổ sung của cả bốn thành viên chạy xanh.
- [ ] Bộ test host và toàn bộ ma trận student xanh.
- [ ] Crash suite đạt `20/20`; T11–T12 xanh trên từng kiến trúc.
- [ ] Benchmark đủ bốn kiến trúc, ít nhất 10 claim và đúng năm seed yêu cầu.
- [ ] ADR, research card và báo cáo nhóm khớp bằng chứng thực tế; giữ nguyên các nhãn máy đọc.
- [ ] Mỗi thành viên có báo cáo cá nhân, commit kỹ thuật và test được ghi trong `TEAM.md`.
- [ ] `check_submission` đạt `0 FAIL`.
- [ ] Không commit secret, trace, SQLite, môi trường ảo hay dữ liệu hidden.
- [ ] Mỗi thành viên tự nộp cùng link repo nhóm trên LMS theo yêu cầu bài.

Các tiêu chí này là điều kiện tự kiểm trước khi nộp. Shape được chọn vẫn phải qua ba điều kiện must-pass và đạt pass rate hidden tối thiểu `0.75` khi giảng viên chấm; không suy ra điểm hidden từ benchmark public.

## 6. Tài liệu đối chiếu

- [README dự án](README.md)
- [Checkpoint](CHECKPOINTS.md)
- [Luật làm bài](RULES.md)
- [Tiêu chí chấm](RUBRIC.md)
- [Yêu cầu nộp bài](SUBMISSION.md)
- [Thông tin và bảng đóng góp của nhóm](TEAM.md)
- [Hướng dẫn chạy code](src/README.md)
