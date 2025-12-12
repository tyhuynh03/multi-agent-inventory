Xây dựng hệ thống quản lý kho thông minh sử dụng Multi-Agent System

GVHD & SVTH
Logo trường (đã cập nhật)
---

Đặt vấn đề & Lý do chọn đề tài

**Bối cảnh:** Kho hàng hiện đại dữ liệu lớn, khó tra cứu thủ công.
**Vấn đề:** Các hệ thống WMS truyền thống cứng nhắc, cần biết SQL/Code.
**Giải pháp:** Ứng dụng AI (LLM + Multi-Agent) để tương tác bằng ngôn ngữ tự nhiên.
---

Mục tiêu & Phạm vi

**Mục tiêu:** Xây dựng Chatbot hỏi đáp tồn kho, vẽ biểu đồ, phân tích rủi ro.
**Phạm vi:** Dữ liệu kho hàng (Inventory, Sales, Products), hỗ trợ tiếng Anh.
---

Các công nghệ cốt lõi

**LLM (Large Language Model):** Khả năng hiểu ngôn ngữ (GPT-4o/Gemini).
**RAG (Retrieval-Augmented Generation):** Kỹ thuật trích xuất thông tin từ tài liệu/CSDL để giảm ảo giác.
**Multi-Agent System:** Kiến trúc nhiều Agent phối hợp (Orchestrator, SQL, Viz, Analytics).
---

Kiến trúc tổng thể

Hình ảnh: *Architecture Diagram* (Hình 3.2 trong báo cáo).
Mô tả: User -> Streamlit -> Orchestrator -> Agents -> Database.
---

Thiết kế các Agent (Role & Responsibility)

**Orchestrator:** Điều phối, phân loại Intent.
**SQL Agent:** Chuyên Text-to-SQL (dùng RAG few-shot).
**Viz Agent:** Chuyên vẽ biểu đồ (Plotly).
**Analytics Agent:** Chuyên tính toán chỉ số kho (Stock Cover).
---

Quy trình nghiệp vụ (Workflow)

Hình ảnh: *Activity Diagram* (Hình 3.5 mới cập nhật).
Giải thích luồng đi của một câu hỏi từ lúc nhập đến lúc ra kết quả.
---

Thiết kế Cơ sở dữ liệu

Hình ảnh: *ERD* (Hình 3.1).
Liệt kê 4 bảng chính: `warehouses`, `skus`, `inventory`, `sales`.
---

Giao diện người dùng (Demo UI)

Hình ảnh: *Screenshot giao diện* (Hình 3.3 - có logo trường).
Các tính năng: Chat, Sidebar history, Settings.
---

Môi trường & Dữ liệu

**Dataset:** Kaggle Inventory Data (đã làm sạch).
**Tech Stack:** Python, LangChain, Streamlit, PostgreSQL, Docker.
---

Các kịch bản kiểm thử (Scenarios)

**Query:** "Total revenue last month?" -> SQL chính xác.
**Visualize:** "Chart of sales by city" -> Biểu đồ cột/tròn.
**Analytics:** "Which items are critical?" -> Bảng phân tích rủi ro.
---

So sánh với phương pháp truyền thống

**Truyền thống:** Cần IT viết báo cáo, cứng nhắc, chậm.
**Multi-Agent:** Tự phục vụ (Self-service), linh hoạt, tức thì.
---

Kết luận & Hướng phát triển

**Kết quả:** Hệ thống chạy ổn định, trả lời đúng >80% câu hỏi test.
**Hạn chế:** Độ trễ còn cao (~5s).
**Tương lai:** Voice search, Mobile App, Dự báo nhu cầu (ML).
---

Demo & Q&A

Chuyển sang demo trực tiếp trên Web App.
Cảm ơn và trả lời câu hỏi.
