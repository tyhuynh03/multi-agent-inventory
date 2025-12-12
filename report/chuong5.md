# CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

## 5.1. Kết luận

Sau quá trình nghiên cứu và triển khai, đề tài "Xây dựng hệ thống quản lý kho thông minh sử dụng Multi-Agent System" đã đạt được những kết quả quan trọng sau:

-   **Về mặt công nghệ:**
    -   Đã xây dựng thành công kiến trúc **Multi-Agent** linh hoạt, cho phép phối hợp nhịp nhàng giữa các Agent chuyên biệt (Intent, SQL, Analytics, Viz).
    -   Ứng dụng hiệu quả **LLM (Large Language Model)** kết hợp với kỹ thuật **RAG (Retrieval-Augmented Generation)** để giải quyết bài toán truy vấn dữ liệu chính xác, giảm thiểu hiện tượng ảo giác (hallucination).
    -   Hệ thống có khả năng hiểu và xử lý các câu hỏi tiếng Anh tự nhiên, từ đơn giản đến phức tạp.

-   **Về mặt ứng dụng:**
    -   Hệ thống giúp **"dân chủ hóa dữ liệu"**, cho phép nhân viên kho và quản lý không cần biết SQL vẫn có thể khai thác thông tin nhanh chóng.
    -   Cung cấp các công cụ **phân tích nâng cao** (như Stock Cover Days) và **trực quan hóa dữ liệu** tự động, hỗ trợ đắc lực cho việc ra quyết định nhập/xuất hàng.
    -   Giao diện Chatbot thân thiện, dễ sử dụng, giảm thiểu thời gian đào tạo người dùng mới.

-   **Hạn chế:**
    -   **Độ trễ (Latency):** Việc gọi nhiều Agent và LLM liên tiếp đôi khi khiến thời gian phản hồi còn chậm (trên 5 giây với các câu hỏi phức tạp).
    -   **Chi phí:** Việc sử dụng các mô hình LLM thương mại (như GPT-4) có thể phát sinh chi phí vận hành cao khi quy mô mở rộng.
    -   **Phạm vi ngôn ngữ:** Hiện tại hệ thống mới chỉ hỗ trợ tốt tiếng Anh, khả năng xử lý tiếng Việt chuyên ngành còn hạn chế.

## 5.2. Hướng phát triển

Để hoàn thiện và nâng cao hiệu quả của hệ thống trong tương lai, nhóm nghiên cứu đề xuất các hướng phát triển sau:

-   **Tích hợp nhận diện giọng nói (Voice Interaction):**
    -   Phát triển tính năng **Speech-to-Text** (sử dụng Whisper hoặc Google API) để cho phép nhân viên kho vừa di chuyển vừa đặt câu hỏi bằng giọng nói (Hands-free operation).
    -   Tích hợp **Text-to-Speech** để hệ thống đọc to kết quả trả lời, hữu ích trong môi trường kho hàng bận rộn.

-   **Phát triển ứng dụng di động (Mobile App):**
    -   Chuyển đổi giao diện từ Web (Streamlit) sang ứng dụng di động (Flutter/React Native) để tăng tính linh hoạt.
    -   Tận dụng camera điện thoại để quét mã vạch/QR Code sản phẩm và hỏi trực tiếp thông tin về sản phẩm đó (VD: "Sản phẩm này còn bao nhiêu cái?").

-   **Dự báo tồn kho sử dụng Machine Learning:**
    -   Tích hợp thêm **Forecasting Agent** sử dụng các thuật toán Time Series (như ARIMA, Prophet hoặc LSTM) để dự báo nhu cầu hàng hóa trong tương lai dựa trên lịch sử bán hàng.
    -   Cảnh báo sớm nguy cơ hết hàng (Stock-out) hoặc tồn kho quá mức (Overstock) để tối ưu hóa vốn lưu động.
