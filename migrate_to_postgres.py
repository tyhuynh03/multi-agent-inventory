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

# Cấu hình database
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'inventory_db',
    'user': 'inventory_user',
    'password': 'inventory_pass'
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
        # Xóa dữ liệu cũ
        cur.execute("DELETE FROM warehouses")
        
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
        # Xóa dữ liệu cũ
        cur.execute("DELETE FROM skus")
        
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
        # Xóa dữ liệu cũ
        cur.execute("DELETE FROM inventory")
        
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
        # Xóa dữ liệu cũ
        cur.execute("DELETE FROM sales")
        
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
