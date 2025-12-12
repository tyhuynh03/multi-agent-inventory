# CHƯƠNG 2. CƠ SỞ LÝ THUYẾT

## 2.1. LangChain

### 2.1.1. Khái niệm

LangChain là một framework hiện đại được thiết kế để đơn giản hóa quá trình xây dựng các ứng dụng sử dụng mô hình ngôn ngữ lớn (LLM). Framework này cung cấp một bộ công cụ giúp kết hợp LLM với dữ liệu, bộ nhớ ngữ cảnh và các công cụ ngoại vi nhằm tạo ra các chuỗi xử lý linh hoạt. Điểm nổi bật của LangChain là khả năng trừu tượng hóa các bước tương tác (Chains, Agents, Tools), giúp nhà phát triển nhanh chóng triển khai các workflow NLP phức tạp.

### 2.1.2. Tính năng chính

LangChain cung cấp nhiều thành phần phục vụ trực tiếp cho dự án:

1. **Chain (Xích):** Cho phép kết nối nhiều bước xử lý LLM thành một chuỗi thống nhất, bảo đảm dữ liệu đầu vào/đầu ra được trao đổi xuyên suốt pipeline.
2. **Agents:** Cho phép LLM tự quyết định nên gọi công cụ nào tiếp theo dựa trên trạng thái hiện tại; phù hợp với kiến trúc multi-agent trong hệ thống kho hàng.
3. **Integration đa nguồn dữ liệu:** Hỗ trợ kết nối tới các nguồn dữ liệu đa dạng như PostgreSQL, file CSV, API ngoài… giúp hệ thống truy xuất dữ liệu tức thời.
4. **Memory:** Lưu lại ngữ cảnh hội thoại, phục vụ các tương tác đa lượt và nâng cao trải nghiệm chatbot.

### 2.1.3. Vai trò trong hệ thống

Trong dự án quản lý kho hàng, LangChain là lớp glue kết nối Intent Agent, SQL Agent, Visualization Agent và Response Agent. Việc chuẩn hóa luồng gọi LLM giúp giảm sai sót, đồng thời tận dụng luôn các tiện ích như `ChatGroq`, `SQLDatabase` hay tracing qua LangSmith để giám sát chất lượng.

## 2.2. Large Language Models (LLM)

### 2.2.1. Khái niệm

Large Language Models là các mô hình Transformer quy mô lớn được huấn luyện trên hàng tỷ token. Dự án sử dụng mô hình **Llama 3.1 70B Versatile** chạy qua **Groq API**, cung cấp tốc độ suy luận cao và chi phí hợp lý. Mô hình này đảm nhiệm hầu hết tác vụ thông minh: phân loại intent, sinh câu lệnh SQL, lập kế hoạch biểu đồ, giải thích kết quả cho người dùng.

### 2.2.2. Đặc điểm nổi bật

- **Hiểu ngữ cảnh dài:** Cho phép đưa kèm schema, ví dụ few-shot và câu hỏi người dùng trong cùng một prompt.
- **Độ chính xác cao:** Thích hợp cho các tác vụ mang tính quyết định như sinh SQL hoặc phân loại intent.
- **Tùy chỉnh tham số:** Duy trì `temperature = 0.1` để đảm bảo kết quả nhất quán, đặc biệt quan trọng với Text-to-SQL.
- **Tích hợp Groq:** Groq cung cấp hạ tầng inference chuyên dụng, giảm độ trễ phản hồi và hỗ trợ free-tier cho nhóm nghiên cứu.

### 2.2.3. Ứng dụng trong dự án

1. **Intent Classification Agent:** Nhận câu hỏi và trả về `intent`, `confidence`, `reasoning`.
2. **SQL Agent:** Sinh câu truy vấn dựa trên prompt mẫu, few-shot và metadata.
3. **Visualization Agent:** Phân tích cấu trúc DataFrame rồi đề xuất loại biểu đồ phù hợp.
4. **Response Agent & Analytics Agent:** Biến kết quả dạng bảng thành mô tả ngắn gọn, hỗ trợ người dùng không rành SQL.

## 2.3. Prompt Engineering

### 2.3.1. Khái niệm

Prompt Engineering là kỹ thuật thiết kế, tối ưu và chuẩn hóa nội dung đầu vào cho LLM nhằm đạt kết quả ổn định. Trong dự án, phần prompt được chuẩn hóa thành các mẫu (template) cất tại thư mục `prompts/` để dễ bảo trì.

### 2.3.2. Các kỹ thuật sử dụng

1. **Few-shot learning với Semantic Search:** Ví dụ SQL được truy xuất qua RAG bằng SentenceTransformer `all-MiniLM-L6-v2`, chỉ lấy top-k ví dụ tương tự nhất để giảm token nhưng vẫn bám sát ngữ cảnh.
2. **Structured Prompt Template:** Prompt của SQL Agent quy định chặt format output (một câu lệnh `SELECT` nằm trong block ```sql```), tránh LLM sinh văn bản thừa.
3. **Context Enrichment:** Tiêm schema và mô tả bảng từ `data/metadata_db.yml` vào đầu prompt để LLM nắm chính xác tên bảng/cột.
4. **Hyperparameter Tuning:** Khoá `temperature` thấp, cấu hình retry khi không parse được SQL, log lại toàn bộ prompt/response qua LangSmith để dễ truy vết.

### 2.3.3. Hiệu quả đạt được

Nhờ các kỹ thuật trên, tỷ lệ truy vấn SQL hợp lệ tăng rõ rệt, hạn chế tình trạng “hallucination”. Đồng thời, Prompt Engineering giúp thống nhất phong cách trả lời giữa các agent, thuận tiện cho việc mở rộng hoặc thay thế mô hình sau này.

## 2.4. Hệ thống Multi-Agent

### 2.4.1. Khái niệm

Multi-Agent System là kiến trúc gồm nhiều tác nhân (agent) tự chủ, mỗi agent thực hiện một nhiệm vụ chuyên biệt và phối hợp thông qua một luồng điều phối chung. Kiến trúc này phù hợp với các bài toán phức tạp như Text-to-SQL vì có thể tách rõ trách nhiệm từng bước.

### 2.4.2. Kiến trúc hệ thống

Hệ thống kho hàng triển khai các agent sau:

1. **Intent Classification Agent:** Phân loại câu hỏi thành `query`, `visualize`, `schema`, `inventory_analytics`.
2. **SQL Agent:** Tạo câu lệnh SQL và trả kèm debug metadata.
3. **Visualization Agent:** Lập kế hoạch biểu đồ dựa trên DataFrame.
4. **Analytics Agent:** Tính toán chỉ số stock cover days, cảnh báo tồn kho thấp.
5. **Response Agent:** Biên soạn câu trả lời tự nhiên và bảng markdown.
6. **Orchestrator Agent:** Nhận đầu vào từ người dùng, gọi chuỗi agent phù hợp, thu thập log từng bước.

### 2.4.3. Ưu điểm

- **Chuyên môn hóa:** Mỗi agent tối ưu cho một nhiệm vụ, dễ kiểm thử độc lập.
- **Khả năng mở rộng:** Có thể bổ sung agent mới (ví dụ “Anomaly Detector”) mà không ảnh hưởng phần còn lại.
- **Khả năng theo dõi:** Orchestrator lưu timing từng bước, hỗ trợ đo độ trễ và tối ưu hiệu năng.
- **Tái sử dụng:** Các agent có thể dùng lại trong các dự án Text-to-SQL khác.

## 2.5. Retrieval-Augmented Generation (RAG)

### 2.5.1. Khái niệm

RAG kết hợp hai giai đoạn: truy xuất (retrieval) thông tin liên quan và sinh (generation) câu trả lời dựa trên ngữ cảnh đó. Dự án dùng RAG để tìm ví dụ SQL tương tự giúp LLM sinh truy vấn chính xác hơn.

### 2.5.2. Thành phần chính

1. **SentenceTransformer `all-MiniLM-L6-v2`:** Tạo embedding cho câu hỏi và ví dụ Text-to-SQL, cân bằng giữa độ chính xác và tốc độ.
2. **ChromaDB:** Vector database lưu embedding, metadata câu hỏi và câu lệnh SQL mẫu.
3. **RAG Retriever:** Lớp tiện ích quản lý build index, truy xuất top-k ví dụ, theo dõi số lượng bản ghi.

### 2.5.3. Quy trình vận hành

1. **Indexing:** Đọc `data/examples.jsonl`, sinh embedding và nạp vào ChromaDB.
2. **Retrieval:** Khi có câu hỏi mới, tạo embedding, truy tìm top-k (mặc định 2) ví dụ có độ tương đồng ≥ 0.3.
3. **Few-shot Prompting:** Format ví dụ thành block `Question …` + ```sql```, chèn vào prompt của SQL Agent.

### 2.5.4. Lợi ích

- Giảm tỷ lệ sinh SQL sai bảng/cột.
- Dễ dàng mở rộng chỉ bằng cách thêm ví dụ mới vào file `.jsonl`.
- Tiết kiệm token vì chỉ lấy ví dụ thật sự liên quan thay vì nhồi toàn bộ dataset.

## 2.6. Các công nghệ hỗ trợ

### 2.6.1. PostgreSQL và SQLAlchemy

- **PostgreSQL:** Lưu trữ dữ liệu kho hàng với bốn bảng chính `warehouses`, `skus`, `inventory`, `sales`, hỗ trợ ràng buộc quan hệ và phép phân tích nâng cao.
- **SQLAlchemy / LangChain SQLDatabase:** Tạo kết nối thống nhất, hỗ trợ connection pooling và thực thi câu lệnh an toàn từ Python.

### 2.6.2. Streamlit

Streamlit được dùng xây dựng giao diện web truy vấn dữ liệu. Người dùng nhập câu hỏi, xem bảng kết quả, biểu đồ và nhật ký phân tích trên cùng một trang. Cấu hình caching giúp giảm thời gian phản hồi khi chạy lặp lại truy vấn.

### 2.6.3. Plotly & Matplotlib

Visualization Agent dựa vào Plotly để dựng biểu đồ tương tác (bar, line, pie, scatter, heatmap). Với những biểu đồ tĩnh nhẹ, Matplotlib hỗ trợ xuất ảnh nhanh. Bộ đôi này đảm bảo đáp ứng cả nhu cầu phân tích và thuyết trình.

### 2.6.4. ChromaDB & Sentence Transformers

Hai thành phần này phối hợp tạo nên tầng semantic search cho RAG. ChromaDB lưu trữ lâu dài tại `data/chroma_db`, đảm bảo sau mỗi lần khởi động lại hệ thống vẫn giữ được chỉ mục. Sentence Transformers cung cấp embedding vector 384 chiều, phù hợp với nhu cầu real-time.

---

**Tóm tắt:** Chương 2 đã trình bày tập hợp các nền tảng lý thuyết trọng tâm của dự án gồm LangChain, LLM Groq Llama, kỹ thuật Prompt Engineering, kiến trúc Multi-Agent và cơ chế RAG kết hợp với các công nghệ hỗ trợ như PostgreSQL, Streamlit, Plotly, ChromaDB. Những nền tảng này là cơ sở để thiết kế nên hệ thống quản lý kho hàng đa agent trong các chương tiếp theo.

