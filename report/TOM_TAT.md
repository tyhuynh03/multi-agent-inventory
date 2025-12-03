# TÓM TẮT ĐỒ ÁN

**Tên đề tài:** Xây dựng hệ thống quản lý kho thông minh sử dụng Multi-Agent System

---

### TÓM TẮT

Nhu cầu về các hệ thống quản lý tồn kho thông minh ngày càng gia tăng khi doanh nghiệp tìm kiếm khả năng phân tích dữ liệu theo thời gian thực, tự động hóa báo cáo và công cụ hỗ trợ ra quyết định mang tính tương tác. Nghiên cứu này đề xuất một kiến trúc đa tác tử (Multi-Agent) cho phép người dùng tương tác với cơ sở dữ liệu tồn kho bằng ngôn ngữ tự nhiên, mà không cần hiểu biết về SQL hoặc cấu trúc dữ liệu.

Hệ thống tích hợp bốn nhóm công nghệ chính: (i) kiến trúc đa tác tử phân rã bài toán thành các tác tử chuyên trách như nhận diện ý định, sinh câu lệnh Text-to-SQL, kiểm tra và xác thực truy vấn, thực thi SQL và trực quan hóa dữ liệu; (ii) cơ chế RAG (Retrieval-Augmented Generation) sử dụng tìm kiếm ngữ nghĩa dựa trên embedding nhằm tăng cường khả năng hiểu schema và giảm lỗi sinh SQL; (iii) cơ sở dữ liệu PostgreSQL lưu trữ dữ liệu tồn kho có cấu trúc; và (iv) Groq API đóng vai trò là hạ tầng suy luận hiệu năng cao, cung cấp thời gian phản hồi thấp và ổn định cho các tác vụ xử lý ngôn ngữ.

Hệ thống được triển khai với LangChain làm nền tảng điều phối tác tử và Streamlit làm giao diện tương tác, hỗ trợ người dùng truy vấn tồn kho, theo dõi biến động, tạo báo cáo phân tích và hiển thị kết quả thông qua biểu đồ và bảng dữ liệu theo thời gian thực. Kết quả thực nghiệm cho thấy kiến trúc đa tác tử giúp tăng độ chính xác của quá trình sinh SQL, giảm hiện tượng “hallucination” nhờ cơ chế RAG, đồng thời cải thiện trải nghiệm người dùng nhờ thời gian phản hồi thấp khi sử dụng Groq làm bộ máy suy luận. Các kết quả này chứng minh rằng việc kết hợp giữa hệ đa tác tử và các kỹ thuật LLM hiện đại mang lại một giải pháp hiệu quả và có khả năng mở rộng cho quản lý tồn kho thông minh trong môi trường doanh nghiệp thực tế.

**Từ khóa:** Hệ đa tác tử (Multi-Agent Systems), RAG, LLM, Text-to-SQL, Quản lý kho thông minh.

---

### ABSTRACT

The demand for intelligent inventory management systems is increasing as enterprises seek real-time data analysis capabilities, automated reporting, and interactive decision-support tools. This study proposes a Multi-Agent architecture that allows users to interact with inventory databases using natural language, without requiring knowledge of SQL or data structures.

The system integrates four key technology groups: (i) a multi-agent architecture that decomposes the problem into specialized agents such as intent recognition, Text-to-SQL generation, query validation, SQL execution, and data visualization; (ii) a RAG (Retrieval-Augmented Generation) mechanism using embedding-based semantic search to enhance schema understanding and reduce SQL generation errors; (iii) a PostgreSQL database for storing structured inventory data; and (iv) Groq API serving as a high-performance inference infrastructure, providing low latency and stability for language processing tasks.

The system is implemented with LangChain as the agent orchestration platform and Streamlit as the interactive interface, supporting users in querying inventory, tracking fluctuations, creating analytical reports, and displaying results through real-time charts and data tables. Experimental results show that the multi-agent architecture improves the accuracy of SQL generation, reduces "hallucination" phenomena thanks to the RAG mechanism, and enhances user experience with low response times when using Groq as the inference engine. These results demonstrate that combining multi-agent systems with modern LLM techniques offers an effective and scalable solution for intelligent inventory management in real-world enterprise environments.

**Keywords:** Multi-Agent Systems, RAG, LLM, Text-to-SQL, Intelligent Inventory Management.
