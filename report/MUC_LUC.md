# MỤC LỤC

DANH MỤC HÌNH ẢNH  
DANH MỤC BẢNG BIỂU

| Số bảng | Tên bảng | Trang |
| :--- | :--- | :--- |
| **Bảng 4.1** | Kết quả đánh giá hiệu năng hệ thống trên tập kiểm thử | |  
**DANH MỤC TỪ VIẾT TẮT**

| Từ viết tắt | Từ đầy đủ | Ý nghĩa |
| :--- | :--- | :--- |
| **RAG** | Retrieval-Augmented Generation | Tạo văn bản tăng cường truy xuất (Kỹ thuật kết hợp tìm kiếm dữ liệu với mô hình ngôn ngữ) |
| **MAS** | Multi-Agent Systems | Hệ đa tác tử (Hệ thống gồm nhiều tác tử thông minh phối hợp hoạt động) |
| **LLM** | Large Language Model | Mô hình ngôn ngữ lớn |
| **WMS** | Warehouse Management System | Hệ thống quản lý kho hàng |


**CHƯƠNG 1. GIỚI THIỆU**
1.1. Tổng quan
1.1.1. Bối cảnh
Trong kỷ nguyên công nghiệp 4.0, quản trị chuỗi cung ứng và đặc biệt là quản lý kho hàng (Inventory Management) đóng vai trò then chốt đối với hiệu quả hoạt động của doanh nghiệp. Khối lượng dữ liệu phát sinh từ hoạt động nhập, xuất, tồn kho ngày càng lớn, đòi hỏi các công cụ quản lý không chỉ dừng lại ở việc lưu trữ mà còn phải có khả năng phân tích sâu và hỗ trợ ra quyết định nhanh chóng.

Tuy nhiên, các hệ thống quản lý kho (WMS) truyền thống thường có giao diện cứng nhắc, đòi hỏi người dùng phải có kỹ năng truy vấn dữ liệu chuyên sâu hoặc trải qua nhiều bước thao tác thủ công để trích xuất báo cáo. Điều này tạo ra rào cản lớn trong việc tiếp cận thông tin thời gian thực và làm chậm quá trình ra quyết định.

Sự bùng nổ của Trí tuệ nhân tạo (AI), đặc biệt là các Mô hình Ngôn ngữ Lớn (LLM) và kiến trúc Hệ đa tác tử (Multi-Agent Systems), đang mở ra kỷ nguyên mới cho các hệ thống quản trị thông minh. Việc ứng dụng các Agent chuyên biệt để tự động hóa quy trình từ hiểu ngôn ngữ tự nhiên đến phân tích dữ liệu kho đang là xu hướng nghiên cứu cấp thiết và giàu tiềm năng.
1.1.2. Lý do chọn đề tài
Xuất phát từ nhu cầu thực tế về một giải pháp quản lý kho thông minh, linh hoạt và thân thiện với người dùng, đề tài này tập trung nghiên cứu và xây dựng hệ thống Multi-Agent có khả năng tương tác bằng ngôn ngữ tự nhiên.

Các lý do chính để lựa chọn đề tài bao gồm:
- **Giải quyết bài toán tương tác Người - Máy:** Thay vì thao tác trên các menu phức tạp, nhà quản lý có thể đặt câu hỏi trực tiếp (ví dụ: "Hàng nào sắp hết hạn?", "Tỷ lệ quay vòng kho tháng này?") và nhận phản hồi tức thì.
- **Vượt qua giới hạn của LLM đơn lẻ:** Một mô hình ngôn ngữ đơn lẻ thường gặp khó khăn với các tính toán chính xác hoặc logic nghiệp vụ phức tạp. Kiến trúc Multi-Agent cho phép phân chia tác vụ cho các Agent chuyên biệt (Text-to-SQL, Data Analytics, Visualization), giúp nâng cao đáng kể độ chính xác và độ tin cậy.
- **Tính thực tiễn và xu hướng công nghệ:** Việc kết hợp RAG (Retrieval-Augmented Generation) với các kỹ thuật Prompt Engineering hiện đại vào bài toán doanh nghiệp cụ thể giúp kiểm chứng khả năng ứng dụng của AI trong môi trường thực tế, đồng thời tối ưu hóa chi phí vận hành cho doanh nghiệp.
1.2. Mục tiêu nghiên cứu
Mục tiêu tổng quát của đề tài là xây dựng một hệ thống hỗ trợ ra quyết định trong quản lý kho hàng, cho phép người dùng tương tác bằng ngôn ngữ tự nhiên thông qua kiến trúc Multi-Agent.

Các mục tiêu cụ thể bao gồm:
- **Nghiên cứu lý thuyết:** Tìm hiểu sâu về kiến trúc Multi-Agent, cơ chế hoạt động của RAG (Retrieval-Augmented Generation) và các kỹ thuật Prompt Engineering tiên tiến.
- **Phát triển hệ thống:** Xây dựng các Agent chuyên biệt thực hiện các chức năng:
    - Phân loại ý định người dùng (Intent Classification).
    - Chuyển đổi câu hỏi tự nhiên thành truy vấn cơ sở dữ liệu (Text-to-SQL).
    - Phân tích các chỉ số kho hàng nâng cao (Stock Cover, Turnover Rate).
    - Trực quan hóa dữ liệu tự động (Data Visualization).
- **Đánh giá thực nghiệm:** Kiểm thử độ chính xác của các câu lệnh SQL được sinh ra và khả năng xử lý các câu hỏi phức tạp, đa ngữ cảnh của hệ thống trên tập dữ liệu mẫu.
1.3. Phạm vi nghiên cứu
**Phạm vi về nội dung:**
- Đề tài tập trung giải quyết bài toán truy xuất và phân tích thông tin trong quản lý kho hàng.
- Các nghiệp vụ chính được xử lý bao gồm: Tra cứu số lượng tồn kho, theo dõi lịch sử nhập xuất, tính toán vòng quay hàng tồn kho (Inventory Turnover) và dự báo ngày hết hàng (Stock Cover).
- Công nghệ sử dụng: Ngôn ngữ Python, Framework LangChain/LangGraph, Cơ sở dữ liệu PostgreSQL, và giao diện người dùng Streamlit.

**Phạm vi về dữ liệu:**
- Hệ thống được xây dựng và kiểm thử trên bộ cơ sở dữ liệu giả lập (Mock Data) mô phỏng quy trình vận hành của một kho hàng bán lẻ tiêu chuẩn, bao gồm các bảng dữ liệu về Sản phẩm, Kho, Giao dịch nhập/xuất và Nhà cung cấp.

**Giới hạn của đề tài:**
- Hệ thống chưa tích hợp trực tiếp với các thiết bị phần cứng (IoT, RFID) trong kho thực tế.
- Chưa bao gồm các nghiệp vụ kế toán kho phức tạp (như tính giá vốn hàng bán theo FIFO/LIFO) hoặc tối ưu hóa logistics vận chuyển.
1.4. Ý nghĩa khoa học và thực tiễn
**Ý nghĩa khoa học:**
- Đề tài đóng góp vào việc nghiên cứu ứng dụng của các mô hình ngôn ngữ lớn (LLM) trong các bài toán chuyên ngành hẹp (Domain-specific).
- Kiểm chứng hiệu quả của kiến trúc Multi-Agent trong việc xử lý các tác vụ phức tạp đòi hỏi sự phối hợp giữa nhiều thành phần (Logic, Toán học, Truy xuất dữ liệu).
- Cung cấp một case study cụ thể về việc tích hợp RAG để giải quyết vấn đề ảo giác (hallucination) của AI khi truy vấn dữ liệu doanh nghiệp.

**Ý nghĩa thực tiễn:**
- **Tối ưu hóa vận hành:** Giúp giảm thiểu thời gian và công sức cho việc làm báo cáo thủ công, cho phép nhân viên kho và quản lý tập trung vào các công việc chiến lược hơn.
- **Dân chủ hóa dữ liệu (Data Democratization):** Cho phép những người không có kiến thức về SQL hay lập trình vẫn có thể khai thác dữ liệu hiệu quả thông qua ngôn ngữ tự nhiên.
- **Hỗ trợ ra quyết định tức thì:** Cung cấp thông tin chính xác và trực quan theo thời gian thực, giúp doanh nghiệp phản ứng nhanh với các biến động của thị trường và chuỗi cung ứng.

**CHƯƠNG 2. CƠ SỞ LÝ THUYẾT**  
2.1. Tổng quan về Hệ đa tác tử (Multi-Agent Systems)  
2.2. Mô hình Ngôn ngữ lớn (LLM) và kỹ thuật Prompt Engineering  
2.3. Kiến trúc RAG (Retrieval-Augmented Generation)  
2.4. Các Framework phát triển Agent (LangChain, LangGraph)  
2.5. Tổng quan các nghiên cứu liên quan
Phần này tổng hợp các công trình nghiên cứu trong và ngoài nước liên quan đến các công nghệ lõi được sử dụng trong đề tài.

2.5.1. Các nghiên cứu về Text-to-SQL và LLM trong truy vấn dữ liệu
- Trình bày về sự phát triển của bài toán Text-to-SQL: từ các phương pháp Rule-based truyền thống đến các mô hình Deep Learning (Seq2Seq) và gần đây là LLM (GPT-3.5, GPT-4, Llama).
- Đề cập đến các kỹ thuật Prompt Engineering (Zero-shot, Few-shot, Chain-of-Thought) để cải thiện độ chính xác của câu lệnh SQL sinh ra.
- *Ví dụ tham khảo:* Các nghiên cứu trên tập dữ liệu Spider hoặc WikiSQL.

2.5.2. Ứng dụng RAG (Retrieval-Augmented Generation) trong doanh nghiệp
- Tổng quan về các nghiên cứu sử dụng RAG để giải quyết vấn đề "ảo giác" (hallucination) và thiếu kiến thức cập nhật của LLM.
- Các phương pháp tối ưu hóa RAG: Hybrid Search (kết hợp Keyword + Vector), Reranking, và Context Window management.
- Ứng dụng của RAG trong việc tra cứu tài liệu kỹ thuật hoặc quy trình nội bộ.

2.5.3. Hệ đa tác tử (Multi-Agent) trong quản lý chuỗi cung ứng
- Giới thiệu các nghiên cứu về việc sử dụng Multi-Agent Systems (MAS) để mô phỏng và tối ưu hóa chuỗi cung ứng.
- Sự chuyển dịch từ các Agent đơn lẻ sang hệ sinh thái các Agent phối hợp (Collaborative Agents) để giải quyết các tác vụ phức tạp (như vừa truy vấn dữ liệu, vừa phân tích và vẽ biểu đồ).
- *Điểm khác biệt của đề tài:* Nhấn mạnh sự kết hợp giữa MAS và LLM để tạo ra giao diện tương tác tự nhiên cho người dùng cuối.

**CHƯƠNG 3. PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG**  
3.1. Yêu cầu hệ thống  
3.2. Kiến trúc tổng thể  
3.3. Thiết kế chi tiết các Agent  
    3.3.1. Intent Classification Agent (Phân loại ý định)  
    3.3.2. SQL Generation Agent (Tạo truy vấn SQL)  
    3.3.3. Analytics Agent (Phân tích nâng cao: Stock Cover, Turnover)
    3.3.4. Visualization Agent (Trực quan hóa dữ liệu)  
    3.3.5. Response Agent (Tổng hợp câu trả lời)  
3.4. Thiết kế Cơ sở dữ liệu  
3.5. Quy trình nghiệp vụ (Workflow)
3.6. Thiết kế Giao diện (User Interface)  

**CHƯƠNG 4. THỰC NGHIỆM VÀ KẾT QUẢ**  
**CHƯƠNG 4. THỰC NGHIỆM VÀ KẾT QUẢ**
4.1. Môi trường triển khai (Docker, Streamlit, PostgreSQL)
    4.1.1. Cấu hình phần cứng
    4.1.2. Cấu hình phần mềm
4.2. Mô tả và Chuẩn bị dữ liệu
    4.2.1. Nguồn dữ liệu
    4.2.2. Xử lý và Lưu trữ
4.3. Dữ liệu thực nghiệm
4.4. Kết quả thực nghiệm
    4.4.1. Hiệu suất
    4.4.2. Ưu điểm và nhược điểm
    4.4.3. So sánh với các phương pháp truyền thống

**CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN**
5.1. Kết luận
5.2. Hướng phát triển  

**TÀI LIỆU THAM KHẢO**  
**KẾ HOẠCH THỰC HIỆN**

| Tuần | Từ ngày | Đến ngày | Nội dung công việc |
| :---: | :---: | :---: | :--- |
| 1 | 15/08/2025 | 21/08/2025 | Nghiên cứu tổng quan, xác định hướng nghiên cứu và phạm vi đề tài. |
| 2 | 22/08/2025 | 28/08/2025 | Nghiên cứu tài liệu: Multi-Agent Systems, LLM, RAG. |
| 3 | 29/08/2025 | 04/09/2025 | Phân tích yêu cầu hệ thống, xác định các Use Case chính. |
| 4 | 05/09/2025 | 11/09/2025 | Thiết kế kiến trúc tổng thể (System Architecture) và Cơ sở dữ liệu. |
| 5 | 12/09/2025 | 18/09/2025 | Thu thập và xử lý dữ liệu kho hàng từ Kaggle (Sản phẩm, Tồn kho). |
| 6 | 19/09/2025 | 25/09/2025 | Cài đặt môi trường phát triển (Docker, PostgreSQL, Python). Xây dựng Backend cơ bản. |
| 7 | 26/09/2025 | 02/10/2025 | Phát triển **Intent Classification Agent** và **Text-to-SQL Agent**. |
| 8 | 03/10/2025 | 09/10/2025 | Phát triển **Analytics Agent** (tính toán chỉ số) và **Visualization Agent** (vẽ biểu đồ). |
| 9 | 10/10/2025 | 16/10/2025 | Xây dựng module RAG: Vector Database, Document Loader cho tài liệu quy trình. |
| 10 | 17/10/2025 | 23/10/2025 | Phát triển giao diện người dùng (Streamlit/Web App) và tích hợp các Agent. |
| 11 | 24/10/2025 | 30/10/2025 | Kiểm thử đơn vị (Unit Test) và tinh chỉnh Prompt (Prompt Engineering). |
| 12 | 31/10/2025 | 06/11/2025 | Kiểm thử toàn hệ thống (Integration Test) trên tập dữ liệu mẫu. Đánh giá kết quả. |
| 13 | 07/11/2025 | 13/11/2025 | Viết báo cáo: Chương 1, 2, 3 (Tổng quan, Lý thuyết, Thiết kế). |
| 14 | 14/11/2025 | 20/11/2025 | Viết báo cáo: Chương 4, 5 (Thực nghiệm, Kết luận). Chỉnh sửa hình thức báo cáo. |
| 15 | 21/11/2025 | 27/11/2025 | Hoàn thiện Slide thuyết trình, Demo sản phẩm và chuẩn bị bảo vệ. |
**NHẬT KÝ LÀM VIỆC**

| STT | Nội dung công việc | Thời gian dự kiến | Thời gian thực tế | Mức độ hoàn thành |
| :---: | :--- | :---: | :---: | :---: |
| 1 | Tìm hiểu tổng quan, xác định hướng nghiên cứu và phạm vi đề tài. | 15/08/2025 - 21/08/2025 | 15/08/2025 - 21/08/2025 | 100% |
| 2 | Nghiên cứu tài liệu về Multi-Agent Systems, LLM và RAG. | 22/08/2025 - 28/08/2025 | 22/08/2025 - 28/08/2025 | 100% |
| 3 | Phân tích yêu cầu hệ thống và xác định các ca sử dụng (Use Cases). | 29/08/2025 - 04/09/2025 | 29/08/2025 - 04/09/2025 | 100% |
| 4 | Thiết kế kiến trúc hệ thống và cơ sở dữ liệu (Schema Design). | 05/09/2025 - 11/09/2025 | 05/09/2025 - 11/09/2025 | 100% |
| 5 | Thu thập và xử lý dữ liệu kho hàng từ Kaggle. | 12/09/2025 - 18/09/2025 | 12/09/2025 - 18/09/2025 | 100% |
| 6 | Cài đặt môi trường phát triển (Docker, PostgreSQL) và khung dự án. | 19/09/2025 - 25/09/2025 | 19/09/2025 - 25/09/2025 | 100% |
| 7 | Xây dựng Intent Classification Agent và Text-to-SQL Agent. | 26/09/2025 - 05/10/2025 | 26/09/2025 - 05/10/2025 | 100% |
| 8 | Xây dựng Analytics Agent để tính toán chỉ số kho hàng. | 06/10/2025 - 12/10/2025 | 06/10/2025 - 12/10/2025 | 100% |
| 9 | Xây dựng Visualization Agent và Response Agent. | 13/10/2025 - 19/10/2025 | 13/10/2025 - 19/10/2025 | 100% |
| 10 | Phát triển module RAG: Vector DB và xử lý tài liệu quy trình. | 20/10/2025 - 26/10/2025 | 20/10/2025 - 26/10/2025 | 100% |
| 11 | Tích hợp các Agent vào giao diện Streamlit. | 27/10/2025 - 05/11/2025 | 27/10/2025 - 05/11/2025 | 100% |
| 12 | Thực hiện kiểm thử (Unit Test, Integration Test) và đánh giá. | 06/11/2025 - 15/11/2025 | 06/11/2025 - 15/11/2025 | 100% |
| 13 | Viết báo cáo: Các chương Tổng quan, Lý thuyết và Thiết kế. | 16/11/2025 - 23/11/2025 | 16/11/2025 - 23/11/2025 | 100% |
| 14 | Viết báo cáo: Chương Thực nghiệm và Kết luận. | 24/11/2025 - 30/11/2025 | 24/11/2025 - 30/11/2025 | 100% |
| 15 | Hoàn thiện Slide, Code và nộp đồ án. | 01/12/2025 - 07/12/2025 | 01/12/2025 - 07/12/2025 | 100% |