#!/usr/bin/env python3
"""
Script để migrate dữ liệu từ CSV sang PostgreSQL
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from typing import List, Dict, Any
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cấu hình database từ environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'inventory_db'),
    'user': os.getenv('DB_USER', 'inventory_user'),
    'password': os.getenv('DB_PASSWORD', 'inventory_pass')
}

def connect_to_db():
    """Kết nối đến PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ Kết nối thành công đến PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"❌ Lỗi kết nối database: {e}")
        raise

def create_schema(conn):
    """Tạo schema database nếu chưa có"""
    logger.info("🏗️ Đang kiểm tra và tạo schema database...")
    
    with conn.cursor() as cur:
        # Tạo bảng warehouses
        cur.execute("""
        CREATE TABLE IF NOT EXISTS warehouses (
            warehouse_code VARCHAR(10) PRIMARY KEY,
            city VARCHAR(100) NOT NULL,
            province VARCHAR(100) NOT NULL,
            country VARCHAR(100) NOT NULL,
            latitude DECIMAL(10, 8) NOT NULL,
            longitude DECIMAL(11, 8) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Tạo bảng skus
        cur.execute("""
        CREATE TABLE IF NOT EXISTS skus (
            sku_id VARCHAR(10) PRIMARY KEY,
            sku_name VARCHAR(200) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Tạo bảng inventory
        cur.execute("""
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
        )
        """)
        
        # Tạo bảng sales
        cur.execute("""
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
        )
        """)
        
        # Tạo indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_inventory_sku_warehouse ON inventory(sku_id, warehouse_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(order_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_sku_warehouse ON sales(sku_id, warehouse_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_customer_type ON sales(customer_type)")
        
        # Tạo views
        cur.execute("""
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
        JOIN warehouses w ON i.warehouse_id = w.warehouse_code
        """)
        
        cur.execute("""
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
        JOIN warehouses w ON sa.warehouse_id = w.warehouse_code
        """)
        
        conn.commit()
        logger.info("✅ Schema database đã sẵn sàng")

def clear_existing_data(conn):
    """Xóa dữ liệu cũ theo thứ tự ngược lại để tránh lỗi foreign key"""
    logger.info("🗑️ Đang xóa dữ liệu cũ...")
    
    with conn.cursor() as cur:
        # Xóa theo thứ tự ngược lại (từ bảng con đến bảng cha)
        try:
            cur.execute("DELETE FROM sales")
            logger.info("   - Đã xóa dữ liệu sales")
        except Exception as e:
            logger.warning(f"   - Không thể xóa sales (có thể bảng chưa có dữ liệu): {e}")
        
        try:
            cur.execute("DELETE FROM inventory")
            logger.info("   - Đã xóa dữ liệu inventory")
        except Exception as e:
            logger.warning(f"   - Không thể xóa inventory (có thể bảng chưa có dữ liệu): {e}")
        
        try:
            cur.execute("DELETE FROM skus")
            logger.info("   - Đã xóa dữ liệu skus")
        except Exception as e:
            logger.warning(f"   - Không thể xóa skus (có thể bảng chưa có dữ liệu): {e}")
        
        try:
            cur.execute("DELETE FROM warehouses")
            logger.info("   - Đã xóa dữ liệu warehouses")
        except Exception as e:
            logger.warning(f"   - Không thể xóa warehouses (có thể bảng chưa có dữ liệu): {e}")
        
        conn.commit()
        logger.info("✅ Đã xóa dữ liệu cũ")

def load_warehouses(conn):
    """Load dữ liệu warehouses từ CSV"""
    logger.info("📦 Đang load dữ liệu warehouses...")
    
    df = pd.read_csv('data/warehouse.csv')
    logger.info(f"   - Đọc được {len(df)} warehouses")
    
    # Chuẩn hóa dữ liệu
    df['warehouse_code'] = df['Warehouse Code'].str.strip()
    df['city'] = df['City'].str.strip()
    df['province'] = df['Province'].str.strip()
    df['country'] = df['Country'].str.strip()
    
    # Insert vào database
    with conn.cursor() as cur:
        # Insert dữ liệu mới
        insert_query = """
        INSERT INTO warehouses (warehouse_code, city, province, country, latitude, longitude)
        VALUES %s
        """
        
        data = [(row['warehouse_code'], row['city'], row['province'], 
                row['country'], row['Latitude'], row['Longitude']) 
                for _, row in df.iterrows()]
        
        execute_values(cur, insert_query, data)
        conn.commit()
        
    logger.info(f"✅ Đã load {len(df)} warehouses vào database")

def load_skus(conn):
    """Load dữ liệu SKUs từ CSV"""
    logger.info("🏷️ Đang load dữ liệu SKUs...")
    
    df = pd.read_csv('data/sku.csv')
    logger.info(f"   - Đọc được {len(df)} SKUs")
    
    # Chuẩn hóa dữ liệu
    df['sku_id'] = df['SKU ID'].str.strip()
    df['sku_name'] = df['SKU Name'].str.strip()
    
    # Insert vào database
    with conn.cursor() as cur:
        # Insert dữ liệu mới
        insert_query = """
        INSERT INTO skus (sku_id, sku_name)
        VALUES %s
        """
        
        data = [(row['sku_id'], row['sku_name']) 
                for _, row in df.iterrows()]
        
        execute_values(cur, insert_query, data)
        conn.commit()
        
    logger.info(f"✅ Đã load {len(df)} SKUs vào database")

def load_inventory(conn):
    """Load dữ liệu inventory từ CSV"""
    logger.info("📊 Đang load dữ liệu inventory...")
    
    df = pd.read_csv('data/inventory.csv')
    logger.info(f"   - Đọc được {len(df)} inventory records")
    
    # Chuẩn hóa dữ liệu
    df['sku_id'] = df['SKU ID'].str.strip()
    df['warehouse_id'] = df['Warehouse ID'].str.strip()
    df['vendor_name'] = df['Vendor Name'].str.strip()
    
    # Insert vào database
    with conn.cursor() as cur:
        # Insert dữ liệu mới
        insert_query = """
        INSERT INTO inventory (sku_id, vendor_name, warehouse_id, current_inventory_quantity,
                              cost_per_sku, total_value, units, average_lead_time_days,
                              maximum_lead_time_days, unit_price)
        VALUES %s
        """
        
        data = [(row['sku_id'], row['vendor_name'], row['warehouse_id'],
                row['Current Inventory Quantity'], row['Cost per SKU'], row['Total Value'],
                row['Units (Nos/Kg)'], row['Average Lead Time (days)'],
                row['Maximum Lead Time (days)'], row['Unit Price'])
                for _, row in df.iterrows()]
        
        execute_values(cur, insert_query, data)
        conn.commit()
        
    logger.info(f"✅ Đã load {len(df)} inventory records vào database")

def load_sales(conn):
    """Load dữ liệu sales từ CSV"""
    logger.info("💰 Đang load dữ liệu sales...")
    
    df = pd.read_csv('data/sales.csv')
    logger.info(f"   - Đọc được {len(df)} sales records")
    
    # Chuẩn hóa dữ liệu
    df['order_number'] = df['Order Number '].str.strip()  # Có space thừa trong tên cột
    df['sku_id'] = df['SKU ID'].str.strip()
    df['warehouse_id'] = df['Warehouse ID'].str.strip()
    df['customer_type'] = df['Customer Type'].str.strip()
    
    # Convert date
    df['order_date'] = pd.to_datetime(df['Order Date']).dt.date
    
    # Insert vào database (batch processing cho file lớn)
    with conn.cursor() as cur:
        # Insert dữ liệu mới theo batch
        batch_size = 1000
        total_batches = (len(df) + batch_size - 1) // batch_size
        
        insert_query = """
        INSERT INTO sales (order_number, order_date, sku_id, warehouse_id,
                          customer_type, order_quantity, unit_sale_price, revenue)
        VALUES %s
        """
        
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            
            data = [(row['order_number'], row['order_date'], row['sku_id'],
                    row['warehouse_id'], row['customer_type'], row['Order Quantity'],
                    row['Unit Sale Price'], row['Revenue'])
                    for _, row in batch_df.iterrows()]
            
            execute_values(cur, insert_query, data)
            conn.commit()
            
            logger.info(f"   - Đã xử lý batch {batch_num}/{total_batches}")
        
    logger.info(f"✅ Đã load {len(df)} sales records vào database")

def verify_data(conn):
    """Kiểm tra dữ liệu đã load"""
    logger.info("🔍 Đang kiểm tra dữ liệu...")
    
    with conn.cursor() as cur:
        # Đếm records trong mỗi bảng
        tables = ['warehouses', 'skus', 'inventory', 'sales']
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            logger.info(f"   - {table}: {count:,} records")
        
        # Kiểm tra một số queries mẫu
        logger.info("   - Kiểm tra queries mẫu:")
        
        # Top 5 warehouses theo số lượng inventory
        cur.execute("""
        SELECT w.warehouse_code, w.city, SUM(i.current_inventory_quantity) as total_inventory
        FROM warehouses w
        JOIN inventory i ON w.warehouse_code = i.warehouse_id
        GROUP BY w.warehouse_code, w.city
        ORDER BY total_inventory DESC
        LIMIT 5
        """)
        
        results = cur.fetchall()
        for row in results:
            logger.info(f"     - {row[0]} ({row[1]}): {row[2]:,.0f} units")
        
        # Top 5 SKUs theo revenue
        cur.execute("""
        SELECT s.sku_id, s.sku_name, SUM(sa.revenue) as total_revenue
        FROM skus s
        JOIN sales sa ON s.sku_id = sa.sku_id
        GROUP BY s.sku_id, s.sku_name
        ORDER BY total_revenue DESC
        LIMIT 5
        """)
        
        results = cur.fetchall()
        for row in results:
            logger.info(f"     - {row[0]} ({row[1]}): ${row[2]:,.2f}")

def main():
    """Hàm main để chạy migration"""
    logger.info("🚀 Bắt đầu migration dữ liệu sang PostgreSQL...")
    
    try:
        # Kết nối database
        conn = connect_to_db()
        
        # Tạo schema nếu chưa có
        create_schema(conn)
        
        # Xóa dữ liệu cũ
        clear_existing_data(conn)
        
        # Load dữ liệu theo thứ tự (để tránh lỗi foreign key)
        load_warehouses(conn)
        load_skus(conn)
        load_inventory(conn)
        load_sales(conn)
        
        # Kiểm tra dữ liệu
        verify_data(conn)
        
        logger.info("🎉 Migration hoàn thành thành công!")
        
    except Exception as e:
        logger.error(f"❌ Lỗi trong quá trình migration: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("🔌 Đã đóng kết nối database")

if __name__ == "__main__":
    main()
