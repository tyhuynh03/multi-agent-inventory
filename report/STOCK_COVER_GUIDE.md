# 📊 Stock Cover Days - Hướng dẫn sử dụng

## 🎯 Bài toán Stock Cover Days

**Stock Cover Days** = Số ngày tồn kho còn lại dựa trên tốc độ bán hàng hiện tại.

**Công thức:**
```
Stock Cover Days = Current Inventory Quantity / Average Daily Sales
```

**Ví dụ:**
- SKU có: 100 units tồn kho
- Bán trung bình: 5 units/ngày
- → Stock Cover = 100/5 = **20 days**

---

## 📊 Phân loại Stock Status

| Status | Stock Cover Days | Ý nghĩa | Action |
|--------|------------------|---------|--------|
| 🔴 **Critical** | < 15 days | Nguy cơ hết hàng cao | Order ngay! |
| 🟡 **Warning** | 15-30 days | Cần theo dõi | Chuẩn bị order |
| 🟢 **Healthy** | 30-60 days | Lý tưởng | Theo dõi thường xuyên |
| 🟢 **Good** | 60-90 days | Tồn kho dồi dào | OK |
| 🟠 **Overstock** | > 90 days | Tồn quá nhiều | Xử lý tồn kho |
| ⚪ **No Sales** | N/A | Không có sales | Review sản phẩm |

---

## 💡 Câu hỏi mẫu

### Basic - Xem toàn bộ
```
"Calculate stock cover days for all products"
"Show stock cover days"
```
→ Hiển thị top 20 items (exclude No Sales)

### Filter theo ngưỡng
```
"Show products with stock cover less than 30 days"
"Products with low stock cover"
"Which items have coverage under 20 days"
```
→ Chỉ show items thỏa điều kiện

### Top N
```
"Top 10 products with lowest stock cover"
"Top 5 items sắp hết hàng"
"Show me 15 products with shortest coverage"
```
→ Tự động extract số từ câu hỏi

### Filter theo Status
```
"Show critical stock items"
"Products in warning status"
"Critical and warning items"
```
→ Filter theo stock_status

### Kết hợp
```
"Top 20 critical items"
"Show me 10 products with lowest coverage"
"Critical items that need immediate attention"
```

---

## 🔧 Cách hoạt động

### 1. Tính Average Daily Sales
```sql
-- Lấy sales 30 ngày gần nhất
SELECT 
    sku_id,
    warehouse_id,
    SUM(order_quantity) / 30.0 AS avg_daily_sales
FROM sales
WHERE order_date >= (SELECT MAX(order_date) - INTERVAL '30 days' FROM sales)
GROUP BY sku_id, warehouse_id
```

### 2. Tính Stock Cover
```sql
SELECT 
    current_inventory_quantity / avg_daily_sales AS stock_cover_days
```

### 3. Phân loại Status
```sql
CASE 
    WHEN stock_cover_days < 15 THEN 'Critical'
    WHEN stock_cover_days < 30 THEN 'Warning'
    WHEN stock_cover_days < 60 THEN 'Healthy'
    WHEN stock_cover_days < 90 THEN 'Good'
    ELSE 'Overstock'
END
```

---

## ⚙️ Thông số có thể điều chỉnh

Trong `agents/analytics_agent.py`:

```python
class AnalyticsAgent:
    def __init__(self):
        # Điều chỉnh các ngưỡng này
        self.CRITICAL_DAYS = 15   # Thay đổi nếu muốn
        self.WARNING_DAYS = 30
        self.HEALTHY_DAYS = 60
        self.OVERSTOCK_DAYS = 90
```

**Tham số khi gọi:**
```python
# Thay đổi period để tính average sales
agent.calculate_stock_cover_days(period_days=60)  # 60 ngày thay vì 30
```

---

## 📈 Output mẫu

### DataFrame columns:
- `sku_id` - Mã SKU
- `sku_name` - Tên sản phẩm
- `warehouse_id` - Kho
- `vendor_name` - Nhà cung cấp
- `current_inventory_quantity` - Tồn kho hiện tại
- `avg_daily_sales` - Bán TB mỗi ngày
- **`stock_cover_days`** - Số ngày tồn kho còn lại ⭐
- `average_lead_time_days` - Lead time nhập hàng
- `total_value` - Giá trị tồn kho
- **`stock_status`** - Trạng thái (Critical/Warning/...) ⭐

### LLM Summary:
Agent tự động tạo summary với:
- Executive summary
- Top critical insights
- Recommended actions

---

## 🚨 Use Cases quan trọng

### 1. Identify Critical Items
**Câu hỏi:** "Show critical items"
**Output:** Chỉ SKUs có < 15 days

**Hành động:**
- Order ngay lập tức
- Check lead time vs stock cover
- Nếu lead time > stock cover → emergency order

### 2. Planning Restock
**Câu hỏi:** "Top 20 products with lowest stock cover"
**Output:** 20 SKUs cần ưu tiên nhất

**Hành động:**
- Tạo purchase orders
- So sánh với lead time
- Schedule deliveries

### 3. Monitor Trends
**Câu hỏi:** "Products with stock cover less than 45 days"
**Output:** All items dưới ngưỡng

**Hành động:**
- Weekly review
- Adjust safety stock
- Negotiate faster shipping

---

## 🔍 Giải thích kết quả

### Ví dụ 1: Critical Item
```
SKU: 1325AA
Current Inventory: 6 units
Avg Daily Sales: 0.42 units/day
Stock Cover: 14.15 days
Lead Time: 45 days
Status: 🔴 Critical
```

**Phân tích:**
- Chỉ còn 14 days tồn kho
- Cần 45 days để nhập hàng
- Gap: 45 - 14 = **31 days** thiếu hụt
- **Action: ORDER NGAY!** Có thể hết hàng trước khi nhập được

### Ví dụ 2: Healthy Item
```
SKU: 2371CA
Current Inventory: 78,462 units
Avg Daily Sales: 1,074 units/day
Stock Cover: 73 days
Lead Time: 90 days
Status: 🟢 Good
```

**Phân tích:**
- Còn 73 days tồn kho
- Lead time 90 days
- Vẫn safe nhưng nên order trong vòng 2 tuần

---


## 📝 Notes

- **Data**: Sales từ 2021-2023 (historical)
- **Period**: Mặc định 30 ngày cuối
- **Auto-detect**: Dùng `MAX(order_date)` thay vì `CURRENT_DATE`
- **Filter**: Mặc định exclude "No Sales"
- **Limit**: Top 20 items (có thể điều chỉnh)
- **Supported**: English + Vietnamese

---

## 🎯 Next Steps (Tương lai)

Khi stock cover days hoạt động tốt, có thể mở rộng:

- [ ] Restock recommendations (dựa vào stock cover + lead time)
- [ ] Stockout predictions (dự đoán ngày hết hàng)
- [ ] Overstock detection (tồn kho > 90 days)
- [ ] Inventory turnover ratio
- [ ] ABC analysis
- [ ] Safety stock calculator

Nhưng hiện tại: **FOCUS vào Stock Cover Days thôi!** 🎯

