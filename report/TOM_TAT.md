# TÓM TẮT ĐỒ ÁN

**Tên đề tài:** Xây dựng hệ thống quản lý kho thông minh sử dụng Multi-Agent System

---

### TÓM TẮT

Trong bối cảnh chuyển đổi số, việc khai thác dữ liệu kho hàng theo thời gian thực thường gặp rào cản do sự phức tạp của các hệ thống quản trị truyền thống (WMS) và yêu cầu kỹ năng truy vấn SQL chuyên sâu. Đồ án này giải quyết thách thức trên bằng cách xây dựng một Hệ thống Quản lý Kho thông minh dựa trên kiến trúc Đa tác tử (Multi-Agent System) kết hợp với Mô hình Ngôn ngữ Lớn (LLM). Thay vì phụ thuộc vào các báo cáo tĩnh, hệ thống cho phép người dùng tương tác trực tiếp bằng ngôn ngữ tự nhiên để tra cứu tồn kho, phân tích xu hướng và trực quan hóa dữ liệu tức thì. Điểm nổi bật của giải pháp là việc ứng dụng kỹ thuật RAG (Retrieval-Augmented Generation) để cung cấp ngữ cảnh schema chính xác cho LLM, kết hợp với tốc độ suy luận vượt trội của Groq API, giúp giảm thiểu độ trễ và loại bỏ hiện tượng ảo giác thông tin. Kết quả thực nghiệm trên ứng dụng (được xây dựng bằng Streamlit và LangChain) cho thấy hệ thống có khả năng xử lý chính xác các câu hỏi phức tạp, tự động sinh biểu đồ và đưa ra cảnh báo tồn kho với độ tin cậy cao, mở ra hướng đi mới cho việc phổ cập phân tích dữ liệu trong quản trị chuỗi cung ứng.

**Từ khóa:** Hệ đa tác tử (Multi-Agent Systems), RAG, LLM, Text-to-SQL, Quản lý kho thông minh.

---

### ABSTRACT

In the context of digital transformation, real-time inventory data exploitation often faces barriers due to the complexity of traditional Warehouse Management Systems (WMS) and the requirement for specialized SQL querying skills. This project addresses this challenge by developing an Intelligent Inventory Management System based on a Multi-Agent System architecture combined with Large Language Models (LLM). Instead of relying on static reports, the system allows users to interact directly using natural language to query inventory, analyze trends, and visualize data instantly. A key highlight of the solution is the application of RAG (Retrieval-Augmented Generation) techniques to provide accurate schema context for the LLM, combined with the superior inference speed of the Groq API, which minimizes latency and eliminates information hallucination. Experimental results on the application (built with Streamlit and LangChain) demonstrate the system's ability to accurately process complex questions, automatically generate charts, and provide inventory warnings with high reliability, paving the way for democratizing data analysis in supply chain management.

**Keywords:** Multi-Agent Systems, RAG, LLM, Text-to-SQL, Intelligent Inventory Management.
