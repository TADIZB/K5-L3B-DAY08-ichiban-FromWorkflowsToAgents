# Bonus report: B3

- Topic + nguồn (tên, năm, slide): B3 — Verifier/aggregator chống khuếch đại lỗi. Google Research 2026, *Towards a Science of Scaling Agent Systems* (error amplification); slide 17 (Evaluator–optimizer), 22 (Reflection), 42.
- CLAIM của nguồn (1 câu): trong hệ multi-agent, agent độc lập khuếch đại lỗi tới 17,2× còn orchestration tập trung (có bước kiểm tra trung tâm) giảm xuống 4,4×, tức một điểm kiểm chứng tập trung chặn được phần lớn lỗi lan truyền.
- BOUNDARY (model / dataset / setup): số 17,2× và 4,4× đo trên các benchmark và LLM thật trong nghiên cứu đó. Nghiên cứu không xét LogiX-VN, MockLLM hay verifier viết bằng code tất định. Nhóm không kiểm lại các con số này, chỉ kiểm hướng của claim: một verifier tập trung trước bước ghi có kéo lỗi của swarm về mức của shape không có lỗi hay không.
- HYPOTHESIS trên LogiX: thêm verifier bằng code (đối chiếu `delay_days`, `status`, `damage_verified` với order có cấu trúc, quote lại tối đa một vòng) sẽ đưa swarm về pass rate và variance bằng workflow trên cả bộ public và bộ đối kháng. Cost/success tăng so với swarm (thêm 1–2 tool call) và vẫn cao hơn workflow khoảng 2×. Safety counts giữ bằng 0.
- Biến cố định / biến thay đổi: cố định claim, world, seed 11/22/33/44/55, `as_of` 2026-11-15, bảng giá mô phỏng, MockLLM, host (`durability`, `policy`), evaluator `lab8.metrics.trial_pass` + `summarize`, SQLite mới mỗi trial. Biến duy nhất giữa `swarm` và `swarm_verified`: có hay không có bước verifier trước khi ghi. Điểm yếu cố ý của swarm (tin số ngày trong ticket ở seed % 5 == 0) được giữ nguyên trong `swarm_verified` để có lỗi mà đo.
- Lệnh tái lập (copy-paste được, chạy tại `src/`):
  - `python -m bonus.run_b3 --out reports/bonus_b3.json`
  - `python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --seeds 11,22,33,44,55 --out reports/bonus_benchmark.json`
  - `python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --cases bonus/cases.jsonl --world bonus/world.json --seeds 11,22,33,44,55 --out reports/bonus_benchmark_adversarial.json`
  - `python -m pytest -q tests/test_bonus_swarm_verified.py` (72 passed)
- File report + run id: `src/reports/bonus_b3.json` (hai corpus, kèm safety counts và số lần verifier can thiệp); `src/reports/bonus_benchmark.json`, `src/reports/bonus_benchmark_adversarial.json` (công cụ của lab, số khớp `bonus_b3.json`). Commit `cfca584`. Run id dạng `R-swarm_verified-<claim>-s<seed>`; trace minh họa `R-swarm_verified-C-002-s55`, `R-swarm_verified-B-002-s55`.

Bộ đối kháng `bonus/cases.jsonl` có 12 claim, nhãn viết tay theo [business_rules.md](../../docs/business_rules.md), không sinh bằng `compensation.quote`: ticket nói quá số ngày (B-001), nói thiếu (B-002), đúng ngưỡng 3 ngày theo cả hai chiều (B-003, B-004), nói dối hỏng hàng (B-005), nhiều con số trong một câu (B-006), nói quá nhưng hỏng hàng đã verify (B-007), đơn hủy (B-008), đơn đã được hoàn (B-009), đơn đang giao (B-010), nói quá kèm approval hết hạn (B-011), sai chủ đơn (B-012).

## Kết quả

Số lấy từ `src/reports/bonus_b3.json`. Mỗi ô: 5 seed × số claim của corpus. Cost là VND mô phỏng.

| Corpus | Shape | Pass | Pass^5 | Seed min–max | Variance | Cost/success | Tool call TB | Verifier can thiệp (trial) | Bypass / leak |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Public (14 claim) | workflow | 70/70 = 1.000 | 1.000 | 1.000–1.000 | 0 | 27.86 | 2.79 | — | 0 / 0 |
| Public | swarm | 69/70 = 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 4.66 | — | 0 / 0 |
| Public | swarm_verified | 70/70 = 1.000 | 1.000 | 1.000–1.000 | 0 | 57.57 | 5.53 | 1 (đổi tiền 1) | 0 / 0 |
| Đối kháng (12 claim) | workflow | 60/60 = 1.000 | 1.000 | 1.000–1.000 | 0 | 29.17 | 2.92 | — | 0 / 0 |
| Đối kháng | swarm | 54/60 = 0.900 | 0.500 | 0.500–1.000 | 0.040000 | 58.84 | 5.07 | — | 0 / 0 |
| Đối kháng | swarm_verified | 60/60 = 1.000 | 1.000 | 1.000–1.000 | 0 | 63.62 | 6.13 | 9 (đổi tiền 6) | 0 / 0 |

Lỗi của swarm đều nằm ở seed 55: public `R-swarm-C-002-s55` (trả 20.000 thay vì từ chối); đối kháng B-001, B-003, B-006 (trả tiền khi phải từ chối), B-002, B-004 (từ chối khi phải trả), B-011 (host chặn nhờ approval hết hạn nên không mất tiền, nhưng `proposal_amount` và audit `policy_denied` sai nhãn). Ở seed 55 swarm chỉ đúng 6/12 claim đối kháng: một lỗi đọc ticket lan thành sai quyết định ở một nửa số claim của seed đó.

Verifier can thiệp 9 trial trên bộ đối kháng: 6 trial đổi số tiền (đúng 6 trial swarm fail), 3 trial dữ kiện lệch nhưng số tiền không đổi (B-007: hỏng hàng 120.000 lớn hơn phí ship nên số ngày không ảnh hưởng; B-009: quote vẫn 35.000 và host chặn vì đơn đã hoàn; B-010: đơn đang giao nên quote luôn 0). Trace `R-swarm_verified-B-002-s55` ghi `model_override` (delay 2 lấy từ ticket) rồi `verifier_override` `{"fields": ["delay_days"], "used": {"delay_days": 2}, "structured": {"delay_days": 6}, "amount_before": 0, "amount_after": 30000}` trước khi host ghi 30.000.

## Kết luận

**Ủng hộ hướng của claim trên LogiX, trong phạm vi đã đo.** Một điểm kiểm chứng tập trung trước bước ghi đưa swarm từ 0.900 / pass^5 0.500 / variance 0.04 về 1.000 / 1.000 / 0 trên bộ đối kháng, bằng workflow, không tăng safety counts. Cái giá là cost/success tăng 16% so với swarm trên public (57.57 so với 49.57) và 8% trên bộ đối kháng (63.62 so với 58.84); swarm_verified vẫn đắt gấp khoảng 2,1–2,2 lần workflow. Cost/success trên bộ đối kháng tăng ít hơn vì verifier biến 6 trial fail thành pass nên mẫu số lớn hơn.

Verifier đưa swarm về **đúng bằng** workflow, vì nó quote lại từ chính nguồn mà workflow dùng. Đó cũng là câu trả lời cho câu hỏi thứ hai: khi verifier đã thay toàn bộ phần quyết định tiền, swarm không còn đóng góp gì cho quyết định. Phần còn lại của swarm (peer, parse, draft) chỉ tạo chi phí và tạo lỗi để verifier sửa. Trên task này kết quả **không** ủng hộ việc chọn swarm_verified thay workflow; nó ủng hộ nguyên tắc "tiền do code tính từ dữ liệu có cấu trúc" mà ADR đã chọn.

Kết luận đảo ngược nếu: (1) phần model đóng góp giá trị mà code không có, ví dụ phân loại ticket mơ hồ hoặc soạn phản hồi có ích cho khách, và giá trị đó được đo; (2) nguồn có cấu trúc cũng có thể sai, khi đó verifier đối chiếu với chính nguồn sai không sửa được gì và cần verifier độc lập hơn; (3) lỗi nằm ngoài ba trường verifier kiểm (ví dụ chọn sai clause hay sai đơn), khi đó verifier này không bắt được.

## Giới hạn

- MockLLM không phải model thật: lỗi của swarm là lỗi được cài sẵn, tất định, chỉ ở seed % 5 == 0. Variance 0 của workflow và swarm_verified phản ánh code tất định, không phải độ ổn định của model thật. Latency `unavailable`; cost là mô phỏng.
- Bộ đối kháng do nhóm tự viết (12 claim, 60 trial/shape), thiên về lỗi số ngày trễ mà nhóm biết swarm mắc. Không đo được mức "khuếch đại" theo nghĩa của paper (17,2× và 4,4×); chỉ đo được verifier chặn hết lỗi đã cài.
- Verifier chỉ kiểm ba trường quote. Nó không kiểm approval, trần theo đơn, chủ đơn; các phần này host đã kiểm. Bypass 0 trên mọi shape là nhờ host, không phải nhờ verifier.
- Chưa có điểm hidden cho `swarm_verified`; giảng viên chấm bằng grader riêng với `--extra-shape`. Tự kiểm trên `student_drop/` (40 claim × 5 seed, không nhãn): 200 trial, 0 lỗi, 0 `leak_suspect`, status trùng workflow ở 200/200 trial, trong khi swarm lệch 6 trial ở seed 55. Kết quả này chưa được lưu thành file trong `src/reports/` vì không có nhãn để tính pass rate.
