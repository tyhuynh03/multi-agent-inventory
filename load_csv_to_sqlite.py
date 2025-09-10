import argparse
import os
import sqlite3
import pandas as pd


def load_csv_to_sqlite(csv_path: str, db_path: str, table_name: str) -> None:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Không tìm thấy file CSV: {csv_path}")

    df = pd.read_csv(csv_path)
    conn = sqlite3.connect(db_path)
    try:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.commit()
        print(f"Đã nạp {len(df)} dòng vào bảng '{table_name}' trong '{db_path}'.")

        print("\nSchema bảng:")
        cur = conn.execute(f"PRAGMA table_info({table_name});")
        cols = cur.fetchall()
        for cid, name, ctype, notnull, dflt, pk in cols:
            print(f"- {name} {ctype}")

        count = conn.execute(f"SELECT COUNT(1) FROM {table_name};").fetchone()[0]
        print(f"\nSố dòng: {count}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Nạp CSV vào SQLite")
    parser.add_argument("csv_path", help="Đường dẫn CSV, ví dụ: retail_store_inventory.csv")
    parser.add_argument("--db", dest="db_path", default="inventory.db", help="Đường dẫn file SQLite (mặc định: inventory.db)")
    parser.add_argument("--table", dest="table_name", default="inventory", help="Tên bảng mục tiêu (mặc định: inventory)")
    args = parser.parse_args()

    load_csv_to_sqlite(args.csv_path, args.db_path, args.table_name)


if __name__ == "__main__":
    main()
