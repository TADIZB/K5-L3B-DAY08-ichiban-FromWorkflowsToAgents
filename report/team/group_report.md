# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: ichiban
- Thành viên: Đặng Khắc Hoàng Minh (2A202604082, Người 1), Trịnh Minh Đức (2A202604078, Người 2), Nguyễn Việt Hoàng (2A202604104, Người 3), Trương Anh Đức (2A202604096, Người 4). Chi tiết vai trò và bảng đóng góp: [TEAM.md](../../TEAM.md).
- Commit chốt (trùng `report/team/decision_adr.md`): `cfca584`
- Shape chọn: **workflow**

## 2. Mục tiêu và cách tiếp cận

Nhóm cài cùng một quy trình xử lý claim hoàn phí theo ba kiến trúc nhóm viết (A workflow, B single agent, C orchestrator), đối chiếu với D swarm có sẵn. Câu hỏi cần trả lời: kiến trúc **ít tự chủ nhất** nào vẫn làm đúng việc, dựa trên số đo cùng corpus, cùng seed, cùng bảng giá.

Nguyên tắc chung cho cả ba shape:

- **Tiền do code quyết định.** Quote luôn tính bằng `compute_compensation` từ dòng order có cấu trúc. Ticket là dữ liệu người dùng: số ngày trễ, lời khai hỏng hàng, câu kiểu "ignore policy" đều không được dùng để tính tiền.
- **Host là nơi ghi duy nhất.** Shape truyền **quote đầy đủ** vào `durability.issue_refund`; host kiểm approval, trừ phần đã hoàn trên cùng đơn, giữ idempotency theo `refund:{claim_id}`. Shape tự trừ trước thì host trừ thêm lần nữa (T14 fail).
- **Crash phải nhìn thấy được.** Shape chuyển `crash_at` cho host và không bắt `InjectedCrash`; kết nối SQLite đóng trong `finally`.
- **Trace là ranh giới bảo mật.** Chỉ ghi field đã qua allowlist, ghi ở mọi nhánh trả kết quả.

Phân công theo [PHAN_CONG.md](../../PHAN_CONG.md): mỗi người một file shape hoặc một nhóm bằng chứng, làm trên nhánh riêng. Người 4 viết test tích hợp áp dụng cùng bất biến cho cả ba shape và chuyển lỗi về đúng chủ file.

## 3. Giải pháp

| Shape | Người | Cách làm | Ranh giới code / model |
| --- | --- | --- | --- |
| A workflow | Người 1 | Các bước Python cố định: `get_claim_view` → `lookup_order` (kiểm chủ đơn) → `compute_compensation` → `issue_refund` | Không gọi model. Toàn bộ quyết định là code |
| B single | Người 2 | `run_react` tối đa 8 bước, `worker=True` nên dispatcher chỉ cho tool đọc. Vòng lặp chỉ nhận `claim_id`, `principal_id`, `order_id`, không nhận ticket. Đọc order → policy → lịch sử hoàn → `final`; sau vòng lặp code mới tính quote và gọi host | MockLLM được gọi để tính budget cho mỗi quyết định và bản draft; text của nó không bao giờ được thực thi như lệnh. Yêu cầu tool ghi → `failed`/`tool_rejected`; hết bước → `failed`/`step_cap`, không ghi tiền |
| C orchestrator | Người 3 | Handoff dựng bằng `make_handoff` với `facts={}` và tool `lookup_order`, `lookup_policy`, `lookup_refund_history`; `_assert_readonly` kiểm lại trước khi giao. Investigator chỉ đọc; orchestrator tính quote và gọi host | Không giao `compute_compensation` cho investigator, nên kết quả của worker không thể thành số tiền ghi sổ. `HandoffError`/`ToolRejected` → `failed` có trace, không ném exception |

**Trace cố ý không ghi** (cả ba shape): `parent_secret`, `raw_headers`, SĐT, địa chỉ, `internal_note`, tên hàng, `principal_id`, nguyên văn ticket, text output của model. Orchestrator có thêm `_GuardedTrace` quét dấu hiệu như `CANARY_` hay `phone` và thay payload bằng bản redacted. Đây chỉ là lớp phòng thủ thứ hai; lớp chính vẫn là chỉ chép field allowlist.

**Test bổ sung** (tổng 316 test nhóm thêm, tất cả xanh):

| File | Người | Số test | Nội dung chính |
| --- | --- | ---: | --- |
| `test_team_workflow.py` | 1 | 3 | Ticket lệch order, quote đầy đủ cho cap theo đơn, crash/resume |
| `test_team_single.py` | 2 | 27 | Giới hạn bước, chặn tool ghi/tool lạ, final giả mạo, injection qua 5 seed, 5 loại approval lỗi, 3 điểm crash |
| `test_team_orchestrator.py` | 3 | 72 | Handoff allowlist không có secret, investigator không có tool ghi kể cả khi handoff bị sửa, trace/stdout sạch trên 14 claim |
| `test_team_integration.py` | 4 | 142 | Cùng bất biến cho cả 3 shape, đọc ledger/audit/checkpoint thật: 5 kiểu approval hỏng, retry chéo shape, amount conflict, crash ở 3 cửa sổ, 3 shape cùng kết quả trên 14 claim, injection, secret dán trong ticket |
| `test_bonus_swarm_verified.py` | 4 | 72 | Bonus B3 |

## 4. Kết quả

Lệnh chạy tại `src/`, commit `cfca584`:

| Kiểm tra | Kết quả |
| --- | --- |
| `python -m lab8.smoke` | `lab8.smoke pass` |
| `python -m pytest -q` (host + test nhóm) | 370 passed |
| `python -m pytest -q -m student -o addopts=` | 248 passed; mỗi shape 62/62 |
| `python -m lab8.crash_test --count 20 --out reports/crash.json` | `crash_safety` 20/20; T11–T12 xanh trên cả 3 shape |
| `python -m lab8.check_submission` | 0 FAIL |
| `python -m lab8.benchmark --shapes workflow,single,orchestrator --cases tests/student_drop/hidden_claims.jsonl --world tests/student_drop/hidden_world_state.json --out reports/hidden_selfcheck.json` | 3 × 200 trial, 0 lỗi, 0 `leak_suspect` (tự kiểm, không có nhãn) |

Benchmark (`src/reports/benchmark.json`, 14 claim × seed 11/22/33/44/55, `as_of` 2026-11-15, MockLLM, giá mô phỏng):

| Shape | Pass rate | Pass^5 | Seed min–max | Variance | Cost/success (VND mô phỏng) | Mean steps | Model call TB | Tool call TB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| workflow | 1.000 | 1.000 | 1.000–1.000 | 0 | **27.86** | 4.29 | 0.00 | 2.79 |
| single | 1.000 | 1.000 | 1.000–1.000 | 0 | 48.26 | 7.14 | 4.64 | 4.50 |
| orchestrator | 1.000 | 1.000 | 1.000–1.000 | 0 | 57.19 | 5.36 | 2.00 | 5.57 |
| swarm | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 | 3.00 | 4.66 |

Trial fail duy nhất là `R-swarm-C-002-s55`: ở seed 55 swarm tin "trễ 5 ngày" trong ticket thay vì `delay_days = 2` của order và trả 20.000 khi phải từ chối. Ba shape nhóm viết từ chối đúng ở cả 5 seed.

**Quyết định:** chọn **workflow**. Độ đúng bằng single và orchestrator nhưng ít tự chủ nhất, không gọi model, cost/success thấp nhất (bằng khoảng 58% của single và 49% của orchestrator), không có rủi ro `step_cap` hay rò qua handoff. Orchestrator không pass nhiều hơn mà đắt hơn 2,05 lần. Điều kiện làm đảo quyết định và trace chi tiết ở [decision_adr.md](decision_adr.md).

**Nghiên cứu (R4, Người 2):** giữ nguyên topology single, chỉ giảm giới hạn ReAct từ 8 xuống 2 bước: pass rate giảm từ 70/70 còn 10/70, cost/success tăng từ 48,26 lên 210,06 dù tổng chi phí giảm. Chênh lệch giữa các shape có thể đến từ ngân sách thực thi chứ không chỉ từ topology. Xem [research_card.md](research_card.md).

**Bonus B3 (Người 4):** thêm verifier bằng code trước bước ghi của swarm (`swarm_verified`) và đo trên public cùng 12 claim đối kháng nhãn viết tay. Trên bộ đối kháng, swarm đạt 0.900 / pass^5 0.500 / variance 0.04; swarm_verified và workflow đạt 1.000 / 1.000 / 0. Verifier can thiệp 9 trial, đổi tiền ở 6 trial. Cost/success: workflow 29.17, swarm 58.84, swarm_verified 63.62. Verifier đưa swarm về bằng workflow vì nó quote lại từ chính nguồn workflow dùng; điều này củng cố lựa chọn workflow. Xem [bonus_report.md](bonus_report.md).

## 5. Khó khăn và cách xử lý

| Khó khăn | Bằng chứng | Cách xử lý |
| --- | --- | --- |
| Máy Người 1 thiếu `pytest`, cài dependency bị chặn mạng | Báo cáo của Người 1: 3 test workflow chưa chạy được lúc commit `d153a50` | Người 4 chạy lại trong venv sạch: `python -m pytest -q tests/test_team_workflow.py` → 3 passed |
| Máy Người 3 có package `tests` trong site-packages che thư mục `src/tests` | `ImportError: cannot import name 'BY_ID'` khi chạy `python -m pytest` | Chạy trong virtualenv sạch (`python -m venv`, cài `requirements.txt`) |
| Trace workflow chép nguyên ticket và `principal_id`; bộ public không bắt được vì `forbid_substrings` không nằm trong ticket | `pytest -q tests/test_team_integration.py -k ticket_never` → `1 failed, 2 passed` (fail ở workflow) | Event `get_claim_view` chỉ còn `found`, `claim_id`, `has_order_id` (commit `a9dcff2`); số benchmark không đổi |
| `-k single` chọn nhầm test của shape khác vì tên test chứa chữ `single` | `-k single` → 242 test thay vì 62 | Lọc `-k "single and not workflow and not orchestrator and not swarm"` → 62 passed |
| Bonus: lần chạy đầu cả 3 shape fail B-002, B-004, B-007 với `missing_approval` | Trace `R-workflow-B-002-s11` có `"reason": "missing_approval"` | Lỗi dữ liệu do nhóm tự tạo (id `A-B-002` so với `A-B002`); sửa `world.json`, giữ nguyên nhãn |
| Đồng bộ nhánh sau khi viết lại commit message | Nhánh lệch `ahead 3, behind 3` so với GitHub | Không force-push; nhánh được đẩy lại như nhánh mới |

## 6. Tổng hợp đóng góp

| Người | Phần việc | Commit | Test |
| --- | --- | --- | --- |
| 1 — Đặng Khắc Hoàng Minh | Workflow; tích hợp | `d153a50` | `test_team_workflow.py` (3) |
| 2 — Trịnh Minh Đức | Single agent; research card R4 và ablation giới hạn bước | `c6b4c99`, `984d09c` | `test_team_single.py` (27) |
| 3 — Nguyễn Việt Hoàng | Orchestrator, investigator chỉ đọc, bảo mật handoff/trace | `7f39a3a` | `test_team_orchestrator.py` (72) |
| 4 — Trương Anh Đức | Test tích hợp, crash suite, benchmark, ADR, sửa lỗi rò ticket, bonus B3, tổng hợp TEAM và báo cáo nhóm | `87a16b2`, `a9dcff2`, `cfca584` | `test_team_integration.py` (142), `test_bonus_swarm_verified.py` (72) |

Báo cáo cá nhân: [2A202604082_DangKhacHoangMinh.md](2A202604082_DangKhacHoangMinh.md), [2A202604078_TrinhMinhDuc.md](2A202604078_TrinhMinhDuc.md), [2A202604104_NguyenVietHoang.md](2A202604104_NguyenVietHoang.md), [2A202604096_TruongAnhDuc.md](2A202604096_TruongAnhDuc.md).

## 7. Hạn chế và hướng cải thiện

- **MockLLM không phải model thật.** Variance 0 của ba shape nhóm viết phản ánh code tất định; lỗi của swarm là lỗi cài sẵn chỉ ở seed % 5 == 0. Latency `unavailable`; cost là mô phỏng, không phải hóa đơn API.
- **Corpus nhỏ.** 14 claim public (70 trial/shape) và 12 claim đối kháng tự viết. 100% trên public không suy ra được pass rate hidden; điểm hidden do grader giảng viên chấm.
- **Tự kiểm hidden chỉ là tự kiểm.** Trên `student_drop/` (40 claim × 5 seed, `src/reports/hidden_selfcheck.json`), ba shape chạy 200/200 trial không lỗi, 0 `leak_suspect`, cùng status và quote; quét 800 trace không thấy chuỗi nhạy cảm nào; bộ kiểm luật độc lập của nhóm khớp workflow 200/200. Bộ không có nhãn và bộ kiểm do nhóm tự viết, nên đây không phải điểm hidden chính thức. Chi tiết trong ADR.
- **Workflow cứng.** Workflow chỉ xử lý được các nhánh đã viết sẵn. Nếu hidden có loại claim cần đọc thêm nguồn tùy nội dung (homoglyph, principal lẫn), ADR đã nêu điều kiện cân nhắc chuyển sang single/orchestrator.
- **Hướng cải thiện:** mở rộng test tích hợp với claim kiểu homoglyph và principal lẫn; thử handoff hai giai đoạn cho orchestrator (giai đoạn 2 nhận `facts` đã lọc từ order) như Người 3 đề xuất và đo xem có đáng thêm chi phí không.

## 8. Tài liệu tham khảo

- Đề bài và tài liệu lab: `README.md`, `RULES.md`, `RUBRIC.md`, `SUBMISSION.md`, `CHECKPOINTS.md`, `PHAN_CONG.md`, `docs/business_rules.md`, `docs/contracts.md`, `docs/metrics.md`, `docs/bonus_topics.md`.
- Sayash Kapoor và cộng sự, *AI Agents That Matter* (2024), arXiv:2407.01502 (research card R4).
- Google Research 2026, *Towards a Science of Scaling Agent Systems*, theo bài giảng N8 slide 17, 22, 42 (bonus B3).
- Công cụ AI: Codex (Người 1, 2), Claude Code (Người 3, 4); cách tự kiểm tra ghi trong từng báo cáo cá nhân.
