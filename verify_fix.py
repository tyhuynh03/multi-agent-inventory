import pandas as pd
from sqlalchemy import create_engine, text
import os

# Database connection
DB_PATH = "data/inventory.db"
# Use absolute path if relative doesn't work, but try relative first since cwd is usually root
if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}")
    exit(1)

connection_string = f"sqlite:///{DB_PATH}"
engine = create_engine(connection_string)

sql_query = """
SELECT i.sku_id, s.sku_name, SUM(i.current_inventory_quantity) AS total_inventory_quantity 
FROM inventory i 
JOIN skus s ON i.sku_id = s.sku_id 
GROUP BY i.sku_id, s.sku_name 
ORDER BY total_inventory_quantity DESC 
LIMIT 10;
"""

try:
    with engine.connect() as conn:
        df = pd.read_sql(text(sql_query), conn)
        print("Query executed successfully!")
        print(f"Rows returned: {len(df)}")
        print("Columns:", df.columns.tolist())
        print(df.head())
        if len(df) <= 10 and 'total_inventory_quantity' in df.columns:
            print("VERIFICATION PASSED")
        else:
            print("VERIFICATION FAILED: Unexpected result shape or columns")

except Exception as e:
    print(f"VERIFICATION FAILED: {e}")
