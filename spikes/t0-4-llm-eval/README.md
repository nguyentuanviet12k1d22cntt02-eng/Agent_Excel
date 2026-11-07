# T0.4 — Kiểm tra LLM Inception Labs

**Mục tiêu:** kiểm tra key dùng được không, so sánh các mô hình Mercury trên đề b09.

**Chạy:** `.venv\Scripts\python spikes	0-4-llm-eval\check_llm.py` (thêm `--models mercury-3 mercury-2` để chọn mô hình). Key lấy từ biến môi trường `LLM_API_KEY`, `apps/backend/.env` hoặc `key.txt`; script không in key.

**Kết quả và kết luận:** xem [docs/task/t0-4-chon-llm.md](../../docs/task/t0-4-chon-llm.md#6-kết-quả-chạy-thử-07112026). Chọn `mercury-3`, có structured output.
