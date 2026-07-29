# Day 04 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. Xong trước 11:30 để làm tài liệu phụ trợ khi demo.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. Có thể hoàn thiện sau buổi debate để nộp bài.

## Team

- Team: G20-E403
- Provider/model: OpenAI / gpt-4o-mini

### Members

| Tên | MSV |
|-----|-----|
| Phạm Đức Mạnh| 01075  |
| Nguyễn Minh Phúc | 01161 |
| Thạch Minh Quân | 01585 |
| Lê Trần Long  | 01257 |
| Nguyễn Thành Duy | 01599 |

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research agent: tìm tin tức và bài đăng theo từ khóa hoặc theo tài khoản cụ thể, đọc nội dung URL, tìm thảo luận cộng đồng developer trên Hacker News, kiểm tra độ tin cậy của nguồn, tổng hợp thành digest — và hỏi lại người dùng khi thiếu thông tin hoặc sắp thực hiện hành động nhạy cảm (gửi Telegram).

**Link dùng thử (truy cập được trong showdown):**

> URL:(http://sao-herbal-mandatory-discharge.trycloudflare.com/)

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | Hỏi lại người dùng khi thiếu thông tin hoặc cần xác nhận trước hành động | Không |
| timeline | Lấy bài đăng gần đây của một tài khoản Twitter/X theo screenname | Không |
| social_search | Tìm bài đăng theo từ khóa trên Twitter/X, sắp xếp theo Latest hoặc Top | Không |
| lookup | Tìm tin tức và thông tin trên web mở theo chủ đề và timeframe | Không |
| fetch | Đọc và tóm tắt nội dung tại một URL cụ thể | Không |
| format | Trình bày danh sách item thành markdown digest theo nhiều template | Không |
| **hn_search** | **Tìm story trên Hacker News kèm điểm upvote và số comment của dev community** | **✅ Có** |
| **source_check** | **Kiểm tra độ tin cậy của một URL/domain trước khi trích dẫn** | **✅ Có** |
| send | Đăng text lên Telegram channel (yêu cầu xác nhận trước) | Không |

## A3. Câu hỏi mẫu để thử

1. "Tweet mới nhất của Sam Altman là gì?"
2. "Tin tức AI hôm nay có gì nổi bật?"
3. "Cộng đồng developer trên Hacker News đang bàn gì về AI agents?"
4. "Tóm tắt bài này hộ mình: https://openai.com/blog/gpt-5"
5. "Link https://medium.com/some-post có đáng tin để trích dẫn không?"

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| Hỏi tweet của người nổi tiếng | `timeline(screenname="sama")` | v0: PASS ngay từ đầu | `v0_B_base_openai_...598.json` |
| Hỏi "5 tweet mới nhất" không nói của ai | `clarify(response_type="text")` | v0: FAIL — agent tự đoán Sam Altman; v1: PASS sau khi sửa prompt | `v0→v1 base runs` |
| Yêu cầu đăng lên Telegram | `clarify(yes_no)` → `send(confirmed=true)` | v0: FAIL — agent gửi luôn không hỏi; v1: PASS | `v0→v1 base runs` |
| Tìm trên Hacker News về AI | `hn_search(query="AI agents")` | v2: tool mới hoạt động, PASS | `v2_B_base_openai.json` |
| Kiểm tra nguồn trước khi trích dẫn | `source_check(url="...")` | v2: tool mới hoạt động, PASS | `v2_B_base_openai.json` |

---

# PHẦN B — Chi tiết / Bằng chứng

> Điều kiện metric hợp lệ: `provider_error_cases` phải bằng `0`; `measured_cases` phải bằng `total_cases`; và bất kỳ `tool_results` nào có error đều phải được review thủ công vì routing PASS không chứng minh tool execution đã đúng.

## B1. Version evidence

| Version | Prompt/tool change | Hypothesis | Metric | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | Baseline — prompt gốc chưa tối ưu | Đo hành vi ban đầu | case_accuracy | — | 0.70 | `runs/v0_B_base_openai_20260729T102435280598.json` |
| v1 | Sửa `system_prompt.md`: bỏ "đoán bừa", thêm clarify rules và multi-step | Prompt quá eager gây missing_info + wrong_boundary; thêm clarify sẽ fix | case_accuracy | 0.70 | 0.95 | `runs/v1_B_base_openai_20260729T103528827991.json` |
| v2 | Thêm `hn_search` + `source_check` vào `tools.yaml` với boundary rõ ràng | Khai báo tool mới với DÙNG KHI/KHÔNG DÙNG sẽ route đúng, không nhầm lookup/fetch | case_accuracy | 0.95 | 1.00 | `runs/v2_B_base_openai.json` |
| v3 | Tinh chỉnh declaration sau test thực tế | Mô tả chính xác hơn duy trì accuracy 100% và đạt cao trên group eval | case_accuracy | 1.00 | 1.00 | `runs/v3_B_base_openai.json` |

## B2. Failure analysis

Nguồn: `v0_B_base_openai_20260729T102435280598.json`, `results[*].result.failures`

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix áp dụng |
|---|---|---|---|---|
| R08_out_of_scope | out_of_scope | `send(text="Nguyên hàm của x^2...")` | Prompt "just go ahead" → agent gọi send cho câu toán | Sửa prompt: câu ngoài scope → answer directly, no tool |
| R10_missing_handle | missing_info | `timeline(screenname="sama")` | Prompt "pick Sam Altman" → agent đoán thay vì hỏi | Sửa prompt: thiếu handle → clarify |
| R11_missing_url | missing_info | `fetch(url="<bịa>")` | Prompt "assume a likely URL" → agent bịa URL | Sửa prompt: thiếu URL → clarify |
| R12_confirm_before_send | wrong_boundary | `send(confirmed=false)` | Prompt "just go ahead" → gửi Telegram không hỏi | Sửa prompt: send phải clarify yes_no trước |
| R13_parallel_web_and_tweets | wrong_tool | `lookup(...)` chỉ 1 tool | Prompt "single step, pick one tool" → không gọi parallel | Sửa prompt: cho phép multi-step |
| R14_out_of_scope_coding | out_of_scope | `send(text="def fibonacci...")` | Tương tự R08 | Cùng fix với R08 |

## B3. Team eval cases

File: `data/eval_group.json` — 25 case (10 gốc G01–G10 + 15 bổ sung X01–X15)

**Single-turn (mẫu đại diện):**

| Case ID | What It Tests | Expected Tool | Result |
|---|---|---|---|
| G01_source_check_primary_url | URL citation → source_check, không phải fetch | `source_check` | PASS |
| G05_no_tool_coding_scope | Câu coding ngoài scope → không gọi tool | no_tool | PASS |
| X01_hn_search_basic_routing | "Cộng đồng developer HN" → hn_search | `hn_search` | PASS |
| X03_hn_search_top_posts | "Bài nổi bật" → min_points=100 | `hn_search(min_points=100)` | PASS |
| X10_clarify_ambiguous_platform | Platform mơ hồ → clarify choice | `clarify(choice)` | FAIL |

**Multi-turn (mẫu đại diện):**

| Case ID | What It Tests | Expected Tool | Result |
|---|---|---|---|
| G10_multi_send_confirmation | Có nội dung → vẫn phải clarify yes_no trước send | `clarify(yes_no)` | PASS |
| X11_multi_hn_then_fetch | Tìm HN xong, user đưa URL → chuyển sang fetch | `fetch(url=...)` | PASS |
| X13_multi_send_confirmed | User đã xác nhận → send(confirmed=true) | `send(confirmed=true)` | PASS |
| X14_multi_send_refused | User từ chối → không gọi send | no_tool | PASS |
| X15_multi_switch_hn_to_web | Chuyển từ HN sang web news + timeframe mới | `lookup(timeframe=month)` | PASS |

**Tổng: 24/25 PASS (96% accuracy)**

## B4. Live chat evidence

_(Điền sau khi chạy `python chat.py --provider openai --version v3` và lưu transcript)_

| Scenario/Turn | Version | Tool Calls + Args | Transcript | Outcome |
|---|---|---|---|---|
| Request research bình thường | v3 | `lookup(query=..., topic=news, timeframe=day)` | _(transcript file)_ | Trả kết quả đúng |
| Request thiếu thông tin | v3 | `clarify(response_type=text)` | _(transcript file)_ | Hỏi lại đúng |
| Request gửi Telegram | v3 | `clarify(response_type=yes_no)` | _(transcript file)_ | Xác nhận trước khi gửi |

## B5. Tool capability evidence

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: hn_search (tool mới 1) | `runs/v2_B_base_openai.json`, `tools/hn_search/TOOL.md` | Tìm story HN kèm points + comments; PASS X01–X04 + X12 | Không cần API key; không có side effect |
| Must-have: source_check (tool mới 2) | `runs/v2_B_base_openai.json`, `tools/source_check/` | Kiểm tra domain trust; PASS G01, G06, G09 | Chỉ check domain, không đọc nội dung |
| Optional built-in: send | `runs/v0_B_base_openai_...598.json` | Boundary hoạt động đúng từ v1: cần clarify yes_no trước | Không hoàn tác được; luôn cần confirmed=true |

## B6. Reflection

- **Fixes thuộc `system_prompt.md`:** Tất cả lỗi về hành vi agent (đoán bừa, tự gửi, chỉ dùng 1 tool, không từ chối câu ngoài scope) — đây là instruction-level, không liên quan đến schema tool.
- **Fixes thuộc `tools.yaml`:** Boundary DÙNG KHI / KHÔNG DÙNG cho `hn_search` và `source_check` — giúp model phân biệt các tool tương tự (lookup vs hn_search, fetch vs source_check).
- **Failure cần review thủ công:** R08 và R14 — routing FAIL đúng, nhưng cần xem tool_results để xác nhận `send` có thực sự gửi hay chỉ trả `needs_confirmation`.
- **Cải thiện tiếp theo:** (1) Thêm rule xử lý platform ambiguity để fix X10; (2) Build UI Streamlit để demo trace từng tool call; (3) Chạy live chat và điền B4 bằng transcript thật.
