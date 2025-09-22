-- Tạo database và user
CREATE DATABASE inventory_db;
CREATE USER inventory_user WITH PASSWORD 'inventory_pass';
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO inventory_user;

-- Kết nối đến database mới
\c inventory_db;

-- Cấp quyền cho user
GRANT ALL ON SCHEMA public TO inventory_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO inventory_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO inventory_user;

-- Tạo extension cho vector search (nếu cần)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- Tạo các bảng
CREATE TABLE IF NOT EXISTS warehouses (
    warehouse_code VARCHAR(10) PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    province VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skus (
    sku_id VARCHAR(10) PRIMARY KEY,
    sku_name VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    sku_id VARCHAR(10) NOT NULL,
    vendor_name VARCHAR(200) NOT NULL,
    warehouse_id VARCHAR(10) NOT NULL,
    current_inventory_quantity DECIMAL(15, 2) NOT NULL,
    cost_per_sku DECIMAL(15, 2) NOT NULL,
    total_value DECIMAL(15, 2) NOT NULL,
    units VARCHAR(20) NOT NULL,
    average_lead_time_days INTEGER NOT NULL,
    maximum_lead_time_days INTEGER NOT NULL,
    unit_price DECIMAL(15, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_code)
);

CREATE TABLE IF NOT EXISTS sales (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL,
    order_date DATE NOT NULL,
    sku_id VARCHAR(10) NOT NULL,
    warehouse_id VARCHAR(10) NOT NULL,
    customer_type VARCHAR(50) NOT NULL,
    order_quantity DECIMAL(15, 2) NOT NULL,
    unit_sale_price DECIMAL(15, 2) NOT NULL,
    revenue DECIMAL(15, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_code)
);

-- Tạo indexes để tối ưu performance
CREATE INDEX IF NOT EXISTS idx_inventory_sku_warehouse ON inventory(sku_id, warehouse_id);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(order_date);
CREATE INDEX IF NOT EXISTS idx_sales_sku_warehouse ON sales(sku_id, warehouse_id);
CREATE INDEX IF NOT EXISTS idx_sales_customer_type ON sales(customer_type);

-- Tạo view để dễ query
CREATE OR REPLACE VIEW inventory_summary AS
SELECT 
    i.sku_id,
    s.sku_name,
    i.warehouse_id,
    w.city,
    w.province,
    i.vendor_name,
    i.current_inventory_quantity,
    i.cost_per_sku,
    i.total_value,
    i.unit_price
FROM inventory i
JOIN skus s ON i.sku_id = s.sku_id
JOIN warehouses w ON i.warehouse_id = w.warehouse_code;

CREATE OR REPLACE VIEW sales_summary AS
SELECT 
    sa.order_date,
    sa.sku_id,
    s.sku_name,
    sa.warehouse_id,
    w.city,
    w.province,
    sa.customer_type,
    sa.order_quantity,
    sa.unit_sale_price,
    sa.revenue
FROM sales sa
JOIN skus s ON sa.sku_id = s.sku_id
JOIN warehouses w ON sa.warehouse_id = w.warehouse_code;
