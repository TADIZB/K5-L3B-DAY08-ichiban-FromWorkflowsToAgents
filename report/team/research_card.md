# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R4 — Evaluation confounders: thay đổi riêng giới hạn bước có thể tạo chênh lệch kết quả lớn đến mức nào khi topology giữ nguyên? |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Sayash Kapoor và cộng sự, *AI Agents That Matter* (2024), [arXiv:2407.01502v1](https://arxiv.org/abs/2407.01502v1). Nguồn nghiên cứu gốc có thực nghiệm benchmark và phân tích phương pháp đánh giá. Dùng làm nguồn bổ sung cho chủ đề R4; không gán kết quả của lab cho paper mẫu trong bảng trên. |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Nghiên cứu cho thấy chỉ tối ưu accuracy có thể dẫn đến agent phức tạp, tốn kém; cần đánh giá chi phí cùng accuracy và chuẩn hóa thực nghiệm để kết quả tái lập được. |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Paper nghiên cứu các benchmark agent và mô hình trong thiết lập riêng; không nghiên cứu LogiX-VN, MockLLM hay ngưỡng 8 bước. Chọn giới hạn bước làm biến ablation là suy luận thực nghiệm của nhóm từ vấn đề đánh giá công bằng. |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Khi giảm riêng MAX_REACT_STEPS từ 8 xuống 2, pass rate giảm ít nhất 50 điểm phần trăm và cost/success tăng, vì luồng bình thường cần ba lần đọc và một quyết định final. Đây là giả thuyết theo cấu trúc code, không phải dự báo đã đăng ký trước độc lập. |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Giữ nguyên topology single, code, prompt template, MockLLM, bộ tool, host, evaluator lab8.metrics, 14 claim public, world state, ngày policy, giá và seed 11/22/33/44/55. Chỉ thay MAX_REACT_STEPS = 8 hoặc 2 bằng patch trong tiến trình thí nghiệm. Mỗi trial dùng SQLite mới; mỗi nhánh dùng thư mục trace tạm riêng. |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: step_cap trước khi kết thúc điều tra. Đo pass rate, pass^5, seed min–max/variance, cost/success, model/tool calls và số event trace qua benchmark/evaluator có sẵn. Kiểm tra quyền tool, chống lộ dữ liệu và crash bằng test riêng; không suy ra chỉ số hidden từ các test này. |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn, tại `src/`): `python -m tests.test_team_single --ablation`
- Experiment id: `single-step-cap-abbc7b0b8a48`.
- Run id / file report: [nhánh 8 bước](../../src/reports/research_single_steps8.json), [nhánh 2 bước](../../src/reports/research_single_steps2.json). Run id từng trial nằm ở `trials[*].run_id`, ví dụ `R-single-C-001-s11`. Hai nhánh dùng cùng run id cho cùng claim/seed; phân biệt bằng file report và `experiment.max_react_steps`.
- Tái lập: hai JSON được hàm `run_ablation` trong `src/tests/test_team_single.py` sinh tự động từ `lab8.benchmark.run_benchmark`; không sửa tay metric. Metadata lưu SHA-256 code triển khai, bộ chạy thí nghiệm, corpus và world state. Chạy lại sinh experiment id mới; đối chiếu cấu hình và số đo, không đòi UUID giống nhau.

| Metric | Giới hạn 8 bước | Giới hạn 2 bước |
| --- | ---: | ---: |
| Trial pass / tổng trial | 70/70 | 10/70 |
| Pass rate | 100% | 14,2857% |
| Pass^5 | 100% | 14,2857% |
| Seed min–max | 100%–100% | 14,2857%–14,2857% |
| Seed variance | 0 | 0 |
| Tổng chi phí mô phỏng (VND) | 3.378,30 | 2.100,60 |
| Chi phí mỗi trial pass (VND mô phỏng) | 48,2614 | 210,0600 |
| Mean model calls | 4,6429 | 2,9286 |
| Mean tool calls | 4,5000 | 2,7857 |
| Mean event trace | 7,1429 | 3,9286 |
| P95 event trace | 8 | 4 |

**Kết quả so với hypothesis:** phù hợp trên bộ public. Giảm giới hạn xuống 2 làm pass rate giảm 85,7143 điểm phần trăm. Tổng chi phí giảm nhưng chi phí mỗi trial pass tăng từ 48,2614 lên 210,0600 VND mô phỏng. Chi phí của trial fail vẫn nằm trong tử số, theo công thức của lab.

Nhánh 2 bước chỉ pass `C-004` (thiếu mã đơn) và `C-005` (ngoài phạm vi chủ sở hữu), mỗi claim qua cả năm seed. Mười hai claim còn lại, tổng cộng 60 trial, trả `failed` với `step_cap`. Evaluator ghi 35 lần `status failed != resolved` và 25 lần `status failed != denied`. Các nhánh bị cắt dừng trước thao tác hoàn tiền.

**Diễn giải:** topology không thay đổi nhưng số đo thay đổi rõ rệt chỉ vì ngân sách bước. Khi so sánh A/B/C/D, cần ghi rõ ngân sách thực thi trước khi quy chênh lệch cho topology. Thí nghiệm này không đo trực tiếp lợi ích của multi-agent.

**Giới hạn:**

- MockLLM không phải model sản xuất; `latency` là `unavailable`; chi phí là mô phỏng, không phải hóa đơn API.
- MockLLM trả chuỗi đánh dấu, không sinh structured tool call. `decide` là chính sách chọn tool xác định trong code; kết quả phản ánh vòng lặp mô phỏng của lab.
- Hai cấu hình cố ý nằm hai phía ngưỡng số bước cần thiết của luồng hiện tại. Không chứng minh rằng phải có đủ 8 bước; đường xử lý bình thường hiện cần bốn quyết định ReAct, trong đó một quyết định là `final`.
- Giới hạn ReAct đếm số lần gọi `decide`. Metric `steps` của lab đếm event trace; đây là hai cách đếm khác nhau.
- Mỗi nhánh có 14 claim × 5 seed. Benchmark chạy `C-011` và `C-012` như trial thông thường; kịch bản retry/crash thực sự được kiểm bằng T11–T12 và test riêng.
- Không thay đổi model/prompt/host để cải thiện điểm; seed variance bằng 0 chỉ phản ánh chính sách xác định trong setup này.
- Không có dữ liệu hidden hoặc thử nghiệm với model thật, nên chưa suy ra pass rate hidden, latency thực tế hay độ an toàn trong sản xuất.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
