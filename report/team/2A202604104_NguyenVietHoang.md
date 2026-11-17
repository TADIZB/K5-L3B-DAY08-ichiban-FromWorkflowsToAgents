# Báo cáo cá nhân — 2A202604104_NguyenVietHoang

## 1. Thông tin thành viên

- Họ tên: Nguyễn Việt Hoàng
- MSSV: 2A202604104
- Email: viethoangnv0810@gmail.com
- GitHub: viethoang126

## 2. Phần việc phụ trách

Người 3 — **Orchestrator và bảo mật handoff** (theo [PHAN_CONG.md](../../PHAN_CONG.md)).

- `src/lab8/shapes/orchestrator.py`: shape C, gồm orchestrator và investigator chỉ có quyền đọc.
- `src/tests/test_team_orchestrator.py`: test bảo mật handoff/trace, retry, crash/resume của orchestrator.

## 3. Đóng góp cụ thể

**Commit chính:** `7f39a3a` — *Implement orchestrator shape with read-only investigator handoff*.

Luồng xử lý của orchestrator:

1. Đọc claim qua `get_claim_view` (không `SELECT *`). Claim không tồn tại → `failed`; thiếu `order_id` → `needs_info`, không chạy investigator, không ghi ledger.
2. Tạo handoff bằng `make_handoff` với `facts={}` và `allowed_tools = [lookup_order, lookup_policy, lookup_refund_history]`, kiểm tra lại lần nữa bằng `_assert_readonly` rồi mới giao cho `run_readonly_investigators`.
3. Order không nhìn thấy được (không tồn tại hoặc khác principal) → `escalated`, trace chỉ ghi `reason`.
4. Orchestrator tự tính quote bằng `compute_compensation` từ order view của investigator (dữ liệu DB), bỏ qua số ngày trễ ghi trong ticket. Quote 0 → `denied`, không gọi host.
5. Quote > 0 → `durability.issue_refund(conn, claim_id, <quote đầy đủ>, crash_at=crash_at)`. Host trừ phần đã hoàn và kiểm approval. Host từ chối → `denied` (proposal giữ quote đầy đủ), conflict → `failed`. `InjectedCrash` được ghi vào trace rồi ném tiếp, không bị nuốt.
6. Mọi nhánh trả kết quả qua `common.finish()` nên `refund_effects` và `committed_audit_count` luôn lấy từ ledger.

**Quyết định kỹ thuật:**

- **Không giao `compute_compensation` cho investigator.** Investigator chỉ thu thập dữ kiện; tiền do orchestrator quyết định trong code. Như vậy không có đường nào để kết quả của worker trở thành số tiền ghi sổ.
- **`facts={}` trong handoff.** Orchestrator chưa đọc order khi tạo handoff, và không chuyển gì từ ticket sang investigator (ticket là dữ liệu người dùng, có thể chứa lệnh kiểu "ignore policy" như C-009).
- **Trace có lớp chặn riêng (`_GuardedTrace`).** Ngoài việc chỉ chép field allowlist (`ORDER_TRACE_FIELDS`), mỗi payload còn được quét các dấu hiệu `CANARY_`, `parent_secret`, `raw_headers`, `Bearer `, `Authorization`, `phone`, `address`, `internal_note`, `item_name`. Payload dính dấu hiệu bị thay bằng `{"redacted": true}` thay vì ghi ra file.
- **Trace cố ý không ghi:** ticket, `principal_id`, secret/header, SĐT, địa chỉ, ghi chú nội bộ, tên hàng, và text output của MockLLM (chỉ ghi mục đích gọi model qua budget).
- **Lỗi bảo mật không làm sập run.** `HandoffError`/`ToolRejected` được chuyển thành `status=failed`, `error_reason=security_guard:<Lỗi>`, vẫn có trace — vì contract cấm `run_claim` ném exception (trừ `InjectedCrash`).

**Test đã thêm** — `src/tests/test_team_orchestrator.py` (72 test sau khi parametrize):

| Test | Chứng minh |
| --- | --- |
| `test_handoff_is_allowlisted_and_has_no_secret` | Handoff thật (bắt bằng spy) chỉ có field allowlist; không có secret, header, ticket, `principal_id` — trên cả 14 claim |
| `test_investigator_never_gets_a_write_tool` | `allowed_tools` ⊆ read-only, không có `issue_refund`/`append_audit`, không có `compute_compensation` |
| `test_investigator_dispatch_rejects_writes_even_if_handoff_is_tampered` | Handoff bị sửa để thêm `issue_refund` vẫn bị runtime từ chối, ledger không đổi |
| `test_write_tool_in_handoff_turns_into_failed_not_exception` | Cấu hình sai tool ghi → `failed` có trace, không exception, không refund |
| `test_trace_and_stdout_hold_no_secret_or_pii` | Trace + stdout + `RunResult` không chứa secret hay PII của bất kỳ order nào (14 claim × seed 11, 55) |
| `test_trace_records_sanitized_handoff` | Trace ghi handoff `handoff.v1` đã sanitize |
| `test_guarded_trace_redacts_leaked_payload` | Lớp chặn trace thay payload chứa secret/SĐT bằng bản redacted |
| `test_ticket_delay_is_ignored_every_seed` | C-002 (ticket nói trễ 5 ngày, DB nói 2) bị `denied` ở cả 5 seed |
| `test_only_orchestrator_calls_issue_refund_once` | C-008: host được gọi đúng 1 lần với quote đầy đủ 35000; ledger ghi 20000 sau cap |
| `test_unknown_claim_fails_with_trace` | Claim không tồn tại → `failed` có trace hợp lệ |
| `test_retry_keeps_one_refund` | Chạy lại C-011 vẫn chỉ một dòng ledger, một audit |
| `test_amount_conflict_is_failed_and_keeps_committed_row` | Số tiền lệch với dòng đã commit → `failed`, giữ dòng cũ |
| `test_crash_propagates_then_resume_pays_once` | 3 điểm crash (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`): crash được ném ra, trace vẫn ghi, chạy lại chỉ một dòng ledger |

## 4. Bằng chứng

- Commit: `7f39a3a` trên nhánh `main` (`https://github.com/TADIZB/K5-L3B-DAY08-ichiban-FromWorkflowsToAgents/commit/7f39a3a`).
- Lệnh và kết quả (chạy trong `src/`, ngày 2026-11-17):

```text
python -m pytest -q -m student -o addopts= -k orchestrator   -> 62 passed
python -m pytest -q tests/test_team_orchestrator.py          -> 72 passed
python -m pytest -q                                          -> 129 passed (sau khi gộp workflow)
python -m pytest -q -m student -o addopts= -k "orchestrator or workflow" -> 124 passed
```

- Benchmark tự chạy (file tạm, **không phải** `src/reports/benchmark.json` chốt bài do Người 4 tạo):

```text
python -m lab8.benchmark --shapes orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out <scratch>/bench_orch.json
```

| Shape | pass_rate | pass_5 | seed_variance | cost/success (VND giả lập) | mean_steps |
| --- | --- | --- | --- | --- | --- |
| orchestrator | 1.000 | 1.000 | 0.000000 | 57.19 | 5.36 |
| swarm | 0.986 | 0.929 | 0.000816 | 49.57 | 2.80 |

  Swarm trượt `R-swarm-C-002-s55` (tin số ngày trong ticket); `R-orchestrator-C-002-s55` trả `denied` đúng. Orchestrator đắt hơn swarm khoảng 15% do gọi thêm 3 tool đọc và một lần model lập kế hoạch.

## 5. Công cụ AI đã dùng

- **Claude Code (Claude Opus 5.5)**: đọc repo và contract, gợi ý code `orchestrator.py`, viết bộ test `test_team_orchestrator.py`, soạn nháp báo cáo này.
- **Cách tự kiểm tra:**
  - Chạy lại bộ 62 test student của orchestrator, bộ test host và test riêng; đối chiếu từng nhánh `status`/`proposal_amount` với bảng output contract trong [docs/contracts.md](../../docs/contracts.md).
  - Mở trực tiếp file trace `traces/R-orchestrator-C-010-s11.json` và `R-orchestrator-C-005-s11.json` để xác nhận không có `CANARY_`, SĐT, địa chỉ.
  - Một test do AI viết ban đầu bị fail vì kiểm tra chuỗi con `"history"` trùng tên tool `lookup_refund_history`; đã sửa thành kiểm tra theo key — tức là test được đọc và hiểu, không chấp nhận nguyên văn.
  - Số liệu benchmark lấy từ output của công cụ lab, không tự điền.

## 6. Tự đánh giá

- **Hoàn thành:** orchestrator qua 62/62 test student; test bảo mật bổ sung xanh; retry (T11) và crash/resume (T12, cùng ba điểm crash) đúng; trace không chứa secret/PII.
- **Khó khăn:** máy cá nhân có một package tên `tests` trong site-packages của user, che thư mục `src/tests` nên `python -m pytest` lỗi `ImportError: cannot import name 'BY_ID'`. Xử lý bằng cách chạy trong virtualenv sạch (`python -m venv`, cài `requirements.txt`). Đã báo để đưa vào mục 5 báo cáo nhóm.
- **Giới hạn:** kết quả trên là trên corpus public 14 claim và MockLLM; không suy ra điểm hidden. Lớp chặn trace dựa trên danh sách dấu hiệu nên chỉ là lớp phòng thủ thứ hai — lớp chính vẫn là chỉ chép field allowlist.
- **Nếu có thêm thời gian:** thử handoff hai giai đoạn (giai đoạn 2 nhận `facts` đã lọc từ order) và đo xem có đáng thêm chi phí không.
