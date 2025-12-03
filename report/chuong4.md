# CHƯƠNG 4. THỰC NGHIỆM VÀ KẾT QUẢ

## 4.1. Môi trường triển khai (Docker, Streamlit, PostgreSQL)

Để thực hiện hệ thống Multi-Agent quản lý kho hàng ứng dụng LangChain và mô hình ngôn ngữ lớn, nhóm nghiên cứu đã thiết lập một môi trường thực nghiệm chi tiết nhằm đảm bảo mọi thành phần của hệ thống được đánh giá một cách toàn diện. Các yếu tố cấu hình phần cứng và phần mềm được lựa chọn kỹ càng để đáp ứng yêu cầu về hiệu năng xử lý và tính ổn định.

### 4.1.1. Cấu hình phần cứng
Hệ thống được triển khai và kiểm thử trên máy tính cá nhân **Acer Nitro 515-45** với thông số chi tiết:

-   **CPU:** Vi xử lý **AMD Ryzen 5 5600H**, dòng chip hiệu năng cao với 6 nhân và 12 luồng xử lý. Đây là thành phần then chốt giúp hệ thống xử lý mượt mà các tác vụ tính toán song song, đặc biệt là khi Orchestrator phải điều phối nhiều Agent hoạt động cùng lúc.
-   **RAM:** Trang bị **16GB RAM**, đảm bảo không gian bộ nhớ đủ lớn để nạp các thư viện nặng (như LangChain, Pandas) và duy trì hiệu suất ổn định khi xử lý các tập dữ liệu kho hàng có kích thước lớn.
-   **Ổ cứng:** Sử dụng ổ cứng **SSD 512GB**, giúp tăng tốc độ truy xuất dữ liệu, giảm thời gian khởi động container Docker và tối ưu hóa độ trễ khi đọc/ghi các file log hệ thống.
-   **GPU:** Card đồ họa **NVIDIA GeForce GTX 1650** (kiến trúc Turing, 4GB VRAM). Mặc dù hệ thống chủ yếu sử dụng API LLM trên cloud (Groq), nhưng GPU này đóng vai trò quan trọng trong việc hỗ trợ hiển thị giao diện đồ họa mượt mà và có thể tận dụng để chạy các mô hình Embedding cục bộ (như HuggingFace Embeddings) nếu cần thiết.
-   **Hệ điều hành:** **Windows 11 Home Single Language**, cung cấp môi trường hiện đại, tương thích tốt với Docker Desktop và các công cụ phát triển Python mới nhất.

### 4.1.2. Cấu hình phần mềm
Môi trường phần mềm được xây dựng dựa trên các công nghệ mã nguồn mở tiên tiến:

-   **Ngôn ngữ lập trình:** **Python 3.10+**, phiên bản ổn định với hệ sinh thái thư viện phong phú hỗ trợ mạnh mẽ cho AI và Data Science.
-   **Framework phát triển:**
    -   **LangChain:** Framework nòng cốt để xây dựng và quản lý các Agent, Chain, và Memory của hệ thống.
    -   **Streamlit:** Thư viện giúp xây dựng giao diện Web App tương tác nhanh chóng (Rapid Prototyping) hoàn toàn bằng Python.
-   **Cơ sở dữ liệu:**
    -   **PostgreSQL (v14+):** Hệ quản trị cơ sở dữ liệu quan hệ mạnh mẽ, được triển khai trên Docker Container để lưu trữ dữ liệu nghiệp vụ (Inventory, Sales).
    -   **ChromaDB:** Vector Database chuyên dụng để lưu trữ và truy vấn các vector embeddings, phục vụ cho tính năng RAG (Retrieval-Augmented Generation) giúp Agent tra cứu các ví dụ SQL mẫu (Few-shot examples).
-   **Containerization:** **Docker & Docker Compose** được sử dụng để đóng gói môi trường, đảm bảo tính nhất quán khi triển khai trên các máy khác nhau và đơn giản hóa việc quản lý các service (DB, App).

## 4.2. Mô tả và Chuẩn bị dữ liệu
    
### 4.2.1. Nguồn dữ liệu
Thay vì thu thập thủ công, hệ thống sử dụng bộ dữ liệu chuẩn (Benchmark Dataset) từ Kaggle chuyên về quản lý chuỗi cung ứng (Supply Chain). Bộ dữ liệu này mô phỏng sát thực tế hoạt động của một doanh nghiệp bán lẻ với các thành phần:
-   **Warehouses:** Thông tin địa lý của các kho hàng.
-   **SKUs:** Danh mục sản phẩm và nhà cung cấp.
-   **Inventory:** Dữ liệu tồn kho hiện tại (Snapshot) bao gồm số lượng, giá trị, và thời gian cung ứng (Lead Time) của từng mã hàng tại từng kho.
-   **Sales:** Lịch sử đơn hàng và doanh thu theo thời gian.

### 4.2.2. Xử lý và Lưu trữ
Dữ liệu thô ban đầu (dạng CSV) đã được phân chia sẵn thành các bảng, nên quy trình xử lý tập trung vào việc làm sạch và nạp dữ liệu:
1.  **Làm sạch (Cleaning):** Kiểm tra và loại bỏ các bản ghi bị lỗi định dạng hoặc thiếu thông tin quan trọng.
2.  **Lưu trữ (Storage):** Import trực tiếp các file CSV vào các bảng tương ứng trong PostgreSQL (`warehouses`, `skus`, `inventory`, `sales`) và thiết lập khóa chính/khóa ngoại.

## 4.3. Dữ liệu thực nghiệm
Để đánh giá hiệu quả của hệ thống, nhóm nghiên cứu đã xây dựng một bộ **Test Set** gồm 20 câu hỏi truy vấn tự nhiên bằng tiếng Anh, bao phủ các mức độ phức tạp khác nhau:

-   **Mức độ Dễ (10 câu):** Truy vấn thông tin đơn giản trên 1 bảng.
    -   *Ví dụ:* "How many products are in warehouse A?", "List all products with price > 100".
-   **Mức độ Trung bình (6 câu):** Truy vấn kết hợp điều kiện lọc, sắp xếp, hoặc tính toán đơn giản (SUM, AVG).
    -   *Ví dụ:* "What are the top 5 best-selling products?", "Calculate total inventory value".
-   **Mức độ Khó (4 câu):** Truy vấn cần JOIN nhiều bảng, tính toán phức tạp hoặc vẽ biểu đồ.
    -   *Ví dụ:* "Compare revenue between warehouse A and B in Q4", "Show me the stock cover days for critical items".

## 4.4. Kết quả thực nghiệm

### 4.4.1. Hiệu suất
Kết quả kiểm thử thực tế trên bộ Test Set (20 câu hỏi) cho thấy:

| Loại câu hỏi | Số lượng | Độ chính xác (Accuracy) | Thời gian phản hồi TB (Latency) |
| :--- | :---: | :---: | :---: |
| Dễ (Simple Query) | 6 | 100% | ~2.5s (*) |
| Trung bình (Aggregation) | 6 | 100% | ~16.5s |
| Khó (Complex/Viz/Analytics) | 8 | 100% | ~15.5s |
| **Tổng cộng** | **20** | **100%** | **~14.0s** |

*(*) Thời gian phản hồi của câu hỏi đầu tiên (Cold Start) có thể lên tới 40s do quá trình khởi tạo model và kết nối database, nhưng các câu hỏi sau đó ổn định ở mức thấp.*

*Nhận xét:*
-   **Độ chính xác:** Hệ thống đạt độ chính xác tuyệt đối (100%) trên tập kiểm thử, cho thấy khả năng sinh SQL và xử lý logic của các Agent hoạt động rất hiệu quả với các mẫu câu hỏi đã định nghĩa.
-   **Độ trễ:**
    -   Với các câu hỏi tra cứu đơn giản, hệ thống phản hồi rất nhanh (< 3s).
    -   Với các tác vụ phức tạp (Vẽ biểu đồ, Phân tích, Tổng hợp số liệu), thời gian xử lý tăng lên đáng kể (~15-17s). Nguyên nhân chủ yếu đến từ việc gọi LLM nhiều lần (Chain of Thought) và thời gian sinh code/phân tích của mô hình ngôn ngữ lớn.
-   **Khả năng chịu tải:** Hệ thống hoạt động ổn định, không gặp lỗi trong quá trình thực thi liên tục 20 câu hỏi.

### 4.4.2. Ưu điểm và nhược điểm
**Ưu điểm:**
-   Giao diện chat trực quan, dễ sử dụng cho người không chuyên.
-   Khả năng xử lý linh hoạt nhiều loại intent (hỏi số liệu, vẽ biểu đồ, phân tích).
-   Tích hợp RAG giúp giảm thiểu ảo giác so với việc chỉ dùng LLM thuần túy.

**Nhược điểm:**
-   Độ trễ còn khá cao ở các tác vụ phức tạp (do phải gọi qua nhiều bước Agent).
-   Phụ thuộc vào chất lượng của LLM (nếu API bị lỗi hoặc chậm thì hệ thống bị ảnh hưởng).

### 4.4.3. So sánh với các phương pháp truyền thống

Khi so sánh với các hệ thống quản lý kho truyền thống (WMS – Warehouse Management System), mô hình Multi-Agent kết hợp LLM và RAG thể hiện nhiều ưu điểm vượt trội về khả năng tương tác, tính linh hoạt và hiệu quả xử lý. Trong các hệ thống WMS thông thường, người dùng phải thao tác qua nhiều màn hình, biểu mẫu và báo cáo cố định để tìm kiếm thông tin. Điều này đòi hỏi người sử dụng phải được đào tạo quy trình và quen thuộc với giao diện để có thể khai thác dữ liệu một cách hiệu quả. Ngược lại, hệ thống được đề xuất cho phép truy vấn dữ liệu bằng ngôn ngữ tự nhiên, giúp người dùng dễ dàng tiếp cận thông tin mà không cần hiểu về SQL hay quy trình thao tác phức tạp.

Bên cạnh đó, các hệ thống truyền thống thường chỉ cung cấp một số báo cáo chuẩn (static reports) và bị giới hạn về tính linh hoạt. Mọi truy vấn nằm ngoài các báo cáo có sẵn đều phải thực hiện thủ công hoặc thông qua bộ phận IT. Trong khi đó, hệ thống Multi-Agent có khả năng sinh báo cáo động tùy theo yêu cầu, thực hiện phân tích nâng cao và trực quan hóa dữ liệu theo từng câu hỏi cụ thể. Điều này tạo ra lợi thế lớn trong các tình huống cần ra quyết định nhanh, đặc biệt là trong các hoạt động liên quan đến kiểm soát tồn kho và dự đoán nhu cầu.

Một điểm khác biệt đáng chú ý là khả năng phân tích. Các WMS truyền thống chủ yếu hỗ trợ mức phân tích cơ bản, tập trung vào tra cứu số liệu. Ngược lại, mô hình Multi-Agent có thể thực hiện các tác vụ như tính toán Stock Cover Days, phát hiện mặt hàng rủi ro, so sánh hiệu suất giữa các kho hoặc các nhóm sản phẩm. Đồng thời, việc tích hợp cơ chế RAG giúp hệ thống tham chiếu tài liệu nội bộ nhanh chóng, cung cấp câu trả lời chính xác hơn cho những câu hỏi liên quan đến quy trình vận hành.

Về mặt vận hành, mặc dù hệ thống truyền thống có ưu điểm ổn định và ít phụ thuộc vào yếu tố bên ngoài, hệ thống Multi-Agent lại linh hoạt hơn trong mở rộng và nâng cấp, do mỗi Agent đảm nhiệm một nhiệm vụ độc lập. Tuy nhiên, hệ thống đề xuất cũng gặp hạn chế như phụ thuộc API LLM và có độ trễ cao hơn khi xử lý truy vấn phức tạp.

Tổng quan lại, mô hình Multi-Agent mang đến sự thay đổi rõ rệt trong cách khai thác dữ liệu kho hàng, chuyển từ mô hình thao tác thủ công sang mô hình khai thác thông tin thông minh, linh hoạt và trực tiếp hơn. Điều này giúp nâng cao hiệu quả quản trị, giảm thời gian tìm kiếm thông tin và hỗ trợ ra quyết định chính xác hơn trong hoạt động vận hành kho.
