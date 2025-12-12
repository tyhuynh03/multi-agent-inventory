# CHI TIẾT SLIDE BÁO CÁO ĐỒ ÁN (Cấu trúc 5 Chương)
**Đề tài:** Xây dựng hệ thống quản lý kho thông minh sử dụng Multi-Agent System

---

## Slide 1: Trang chủ (Title Slide)
*   **Tiêu đề:** Xây dựng hệ thống quản lý kho thông minh sử dụng Multi-Agent System
*   **GVHD:** [Tên GVHD]
*   **SVTH:** [Tên bạn] - [MSSV]
*   **Hình ảnh:** Logo trường ĐH.

---

## Slide 2: Nội dung trình bày (Overview)
1.  **Introduction:** Giới thiệu (Bối cảnh, Lý do, Mục tiêu).
2.  **Theoretical Basis:** Cơ sở lý thuyết & Công nghệ.
3.  **System Design:** Phân tích & Thiết kế hệ thống.
4.  **Results & Discussion:** Kết quả thực nghiệm & Demo.
5.  **Conclusion:** Kết luận & Hướng phát triển.

---

# PHẦN 1: INTRODUCTION (GIỚI THIỆU)

## Slide 3: Bối cảnh (Context)
*   **Sự bùng nổ dữ liệu:**
    *   Thương mại điện tử và chuỗi cung ứng tạo ra lượng dữ liệu khổng lồ.
    *   Dữ liệu kho hàng (Inventory) biến động liên tục theo thời gian thực.
*   **Nhu cầu quản trị:**
    *   Cần ra quyết định nhanh chóng (Data-driven decision making).
    *   Yêu cầu giám sát chặt chẽ dòng hàng hóa để tối ưu chi phí.

## Slide 4: Lý do chọn đề tài (Motivation)
*   **Thực trạng WMS hiện nay:**
    *   Các hệ thống truyền thống (Legacy WMS) thường có giao diện phức tạp, nhiều menu/form.
    *   Báo cáo thường ở dạng tĩnh (Static Reports), khó tùy biến.
*   **Vấn đề (Pain Points):**
    *   **Rào cản kỹ thuật:** Người quản lý kho thường không biết SQL/IT để tự lấy số liệu mình cần.
    *   **Độ trễ thông tin:** Phải chờ đợi bộ phận IT trích xuất báo cáo.
*   **Giải pháp:** Ứng dụng **Generative AI** để làm cầu nối ngôn ngữ tự nhiên giữa người dùng và dữ liệu.

## Slide 5: Mục tiêu & Phạm vi (Objectives & Scope)
*   **Mục tiêu chính:**
    *   Xây dựng **Chatbot thông minh** cho phép truy vấn tồn kho bằng tiếng Anh.
    *   **Tự động hóa** quy trình phân tích và trực quan hóa dữ liệu (Vẽ biểu đồ).
*   **Phạm vi đề tài:**
    *   **Dữ liệu:** Tập trung vào Inventory (Tồn kho), Sales (Bán hàng), Products (Sản phẩm).
    *   **Đối tượng sử dụng:** Nhân viên kho, Quản lý cấp trung (Không yêu cầu kỹ năng lập trình).

---

# PHẦN 2: THEORETICAL BASIS (CƠ SỞ LÝ THUYẾT)

## Slide 6: Các công nghệ cốt lõi
*   **Large Language Model (LLM):**
    *   Sử dụng các mô hình tiên tiến (GPT-4o/Gemini qua Groq API) để hiểu ngữ nghĩa và suy luận logic.
*   **Multi-Agent System:**
    *   Kiến trúc chia nhỏ bài toán phức tạp thành các tác vụ nhỏ do các Agent chuyên biệt xử lý.
*   **RAG (Retrieval-Augmented Generation):**
    *   Kỹ thuật kết hợp tìm kiếm dữ liệu (Vector DB) để cung cấp ngữ cảnh chính xác cho LLM, giảm thiểu ảo giác.

## Slide 7: So sánh với phương pháp truyền thống
| Tiêu chí | WMS Truyền thống | Hệ thống Multi-Agent (Đề xuất) |
| :--- | :--- | :--- |
| **Tương tác** | Click chuột, Menu, Form | Chat (Ngôn ngữ tự nhiên) |
| **Truy vấn** | SQL hoặc Báo cáo định sẵn | Câu hỏi tự do (Ad-hoc) |
| **Tính linh hoạt** | Thấp (Cấu trúc cứng) | Cao (Tự động sinh code/chart) |

---

# PHẦN 3: SYSTEM DESIGN (THIẾT KẾ HỆ THỐNG)

## Slide 8: Kiến trúc tổng thể (Architecture)
*(Chèn Hình 3.2 - Kiến trúc hệ thống)*
*   **Frontend:** Streamlit Web App (Giao diện Chat).
*   **Orchestrator:** Bộ điều phối trung tâm, quản lý hội thoại.
*   **Agent Layer:** Các Agent thực thi (SQL, Viz, Analytics).
*   **Data Layer:** PostgreSQL (Dữ liệu nghiệp vụ) + ChromaDB (Vector Store).

## Slide 9: Thiết kế Orchestrator & Intent Classification
*   **Orchestrator:**
    *   Đóng vai trò "Nhạc trưởng", nhận yêu cầu và điều hướng.
*   **Intent Classification Agent:**
    *   Phân loại câu hỏi người dùng vào 4 nhóm ý định:
        1.  `Query`: Hỏi đáp số liệu thông thường.
        2.  `Visualize`: Yêu cầu vẽ biểu đồ.
        3.  `Analytics`: Yêu cầu phân tích sâu/cảnh báo.
        4.  `Schema`: Hỏi về cấu trúc dữ liệu.

## Slide 10: Thiết kế SQL Generation Agent (RAG)
*   **Vấn đề:** LLM không biết cấu trúc Database của người dùng.
*   **Giải pháp RAG:**
    1.  **Retrieve:** Tìm kiếm các câu SQL mẫu tương tự trong Vector DB.
    2.  **Prompting:** Cung cấp Schema + SQL mẫu cho LLM.
    3.  **Generation:** LLM sinh ra câu lệnh SQL chính xác có thể chạy được.

## Slide 11: Thiết kế Visualization Agent
*   **Nhiệm vụ:** Chuyển dữ liệu truy vấn được thành biểu đồ trực quan phục vụ phân tích.
*   **Quy trình hoạt động:**
    1.  Nhận dữ liệu dạng bảng (DataFrame) từ SQL Generation Agent.
    2.  LLM phân tích dữ liệu &rarr; sinh đặc tả biểu đồ (JSON Spec):
        *   Loại biểu đồ
        *   Trục X / Trục Y
        *   Nhóm dữ liệu
        *   Thuộc tính hiển thị
    3.  Visualization Agent đọc đặc tả và tạo biểu đồ bằng Plotly (hoặc Matplotlib).
    4.  Trả về Plotly Figure để hiển thị trên Streamlit.

## Slide 12: Thiết kế Analytics Agent
## Slide 12: Thiết kế Analytics Agent
*   **Nhiệm vụ:** Phân tích dữ liệu kho để phát hiện rủi ro (Risk) và tính toán chỉ số quản trị.
*   **Quy trình hoạt động:**
    1.  Nhận dữ liệu thô (Inventory, Sales) từ Database.
    2.  Module **Analytics Engine** tính toán chỉ số phái sinh:
        *   Stock Cover Days = Stock / Daily Sales
        *   Inventory Turnover
    3.  Áp dụng **Business Rules** để phân loại rủi ro (Critical, Warning, Healthy).
    4.  LLM tóm tắt kết quả thành **Executive Summary** (tập trung vào Insight quan trọng).
*   **Quy tắc phân loại (Business Rules):**
    *   🚨 **Critical:** Stock Cover < 15 ngày (Cần nhập hàng gấp).
    *   ⚠️ **Warning:** Stock Cover < 30 ngày (Cần chú ý).
    *   ✅ **Healthy:** Tồn kho an toàn (30 - 60 ngày).

## Slide 13: Mô tả dữ liệu & Lược đồ (Data Schema)
*(Chèn Hình 3.1 - ERD)*
*   **Nguồn dữ liệu:** Kaggle Supply Chain Dataset.
*   **Lược đồ quan hệ (Schema):**
    *   `warehouses`: Thông tin kho bãi.
    *   `skus`: Danh mục sản phẩm.
    *   `inventory`: Bảng dữ liệu tồn kho.
    *   `sales`: Bảng lịch sử bán hàng.

## Slide 14: Quy trình nghiệp vụ (Workflow)
*(Minh họa luồng đi tổng quát)*
1.  **User:** Đặt câu hỏi (VD: "Doanh thu theo tháng?").
2.  **Orchestrator:** Xác định Intent -> Gọi SQL Agent.
3.  **SQL Agent:** Sinh SQL -> Query Database -> Trả về Data.
4.  **Response Agent:** Tóm tắt dữ liệu thành câu trả lời dễ hiểu.

---

# PHẦN 4: RESULTS & DISCUSSION (KẾT QUẢ & THẢO LUẬN)

## Slide 15: Môi trường thực nghiệm
*   **Phần cứng:** Laptop cá nhân (Ryzen 5, 16GB RAM).
*   **Phần mềm:** Docker, PostgreSQL 14, Python 3.10.
*   **Dữ liệu:** Kaggle Supply Chain Dataset.
    *   Đã làm sạch và chuẩn hóa.

## Slide 16: Kịch bản kiểm thử (Test Scenarios)
*   **Bộ Test Set:** 20 câu hỏi đa dạng (Dễ - Trung bình - Khó).
*   **Tiêu chí đánh giá:**
    *   **Độ chính xác (Accuracy):** SQL sinh ra đúng cú pháp và logic.
    *   **Độ trễ (Latency):** Thời gian phản hồi chấp nhận được.

## Slide 17: Kết quả thực nghiệm
*   **Độ chính xác:** **85%** (17/20 câu đạt yêu cầu).
    *   Hoạt động tốt với các câu hỏi rõ ràng.
    *   Đôi khi gặp khó khăn với câu hỏi quá phức tạp hoặc nhập nhằng.
*   **Độ trễ trung bình:** **~5.4 giây**.
    *   Nhanh hơn đáng kể so với quy trình làm báo cáo thủ công (hàng giờ/ngày).

## Slide 18: Demo Ứng dụng - Truy vấn (Query)
*(Chèn hình ảnh: Kết quả truy vấn Lead Time cho danh sách SKU)*
*   **Câu hỏi:** "Show the average and maximum lead times for SKUs 1206BA, 1214CA, 1224AA, and 1234BA."
*   **Điểm nổi bật (Highlights):**
    *   **Xử lý ngôn ngữ tự nhiên:** Trích xuất chính xác 4 mã SKU và các chỉ số cần lấy (Average, Max).
    *   **Sinh SQL tối ưu:** Tự động sử dụng mệnh đề `WHERE ... IN (...)` để lọc dữ liệu hiệu quả.
    *   **Hiệu năng:** Thời gian xử lý chỉ **3.03s** (như trong hình).
*   **Kết quả:** Trả về bảng dữ liệu chính xác, sẵn sàng để ra quyết định nhập hàng.

## Slide 19: Demo Ứng dụng - Phân tích rủi ro (Risk Analytics)
*(Chèn hình ảnh: Bảng tính toán chi tiết Stock Cover)*
*   **Câu hỏi:** "Which items are at risk of running out of stock?"
*   **Kết quả:** Hệ thống trả về **bảng số liệu chi tiết** (Tồn kho, Tốc độ bán, Stock Cover...) để minh bạch hóa lý do cảnh báo.
*   **Phát hiện chính (Key Insights):**
    *   **🚨 Critical:** Mã 1325AA & 1851CA (Stock Cover ~14-17 ngày < Lead Time 45-60 ngày) -> Nguy cơ đứt hàng cao.
    *   **⚠️ Mismatch:** Mã 1244AA (Sức bán cao ~101/ngày nhưng nhập hàng quá lâu 45 ngày).

---

# PHẦN 5: CONCLUSION (KẾT LUẬN)

## Slide 20: Kết luận
*   **Kết quả đạt được:**
    *   Xây dựng thành công hệ thống Multi-Agent quản lý kho.
    *   Chứng minh tính khả thi của việc ứng dụng LLM + RAG trong doanh nghiệp.
    *   Giúp "bình dân hóa" dữ liệu (Data Democratization).
*   **Hạn chế:**
    *   Phụ thuộc vào API bên thứ 3 (chi phí, đường truyền).
    *   Độ trễ cần được tối ưu thêm.

## Slide 21: Hướng phát triển
1.  **Voice Interaction:** Tích hợp nhận diện giọng nói để rảnh tay khi làm việc trong kho.
2.  **Mobile App:** Phát triển ứng dụng di động tiện lợi.
3.  **Advanced Forecasting:** Tích hợp AI dự báo nhu cầu (Forecasting) để hỗ trợ nhập hàng chủ động.

---
**Q&A - Cảm ơn thầy cô và các bạn đã lắng nghe!**
