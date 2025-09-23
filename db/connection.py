import os
import sqlite3
import pandas as pd
from typing import Tuple, Optional, Union
import psycopg2
from psycopg2.extras import RealDictCursor

from langchain_community.utilities import SQLDatabase

from utils.logger import traceable


def get_sqlalchemy_url(db_path: str, db_type: str = "sqlite") -> str:
	"""Tạo SQLAlchemy URL cho SQLite hoặc PostgreSQL"""
	if db_type.lower() == "postgresql":
		return db_path  # db_path đã là connection string
	else:
		abs_path = os.path.abspath(db_path)
		return f"sqlite:///{abs_path}"


def get_db(db_path: str, db_type: str = "sqlite") -> SQLDatabase:
	"""Tạo SQLDatabase object cho SQLite hoặc PostgreSQL"""
	url = get_sqlalchemy_url(db_path, db_type)
	return SQLDatabase.from_uri(url)


def get_postgres_connection():
	"""Tạo kết nối trực tiếp đến PostgreSQL"""
	try:
		conn = psycopg2.connect(
			host='localhost',
			port=5432,
			database='inventory_db',
			user='inventory_user',
			password='inventory_pass'
		)
		return conn
	except Exception as e:
		raise Exception(f"Không thể kết nối đến PostgreSQL: {e}")


@traceable(name="sql.exec")
def run_sql(db: SQLDatabase, sql: str) -> Tuple[pd.DataFrame, Optional[str]]:
	first_token = sql.strip().lower()
	if not (first_token.startswith("select") or first_token.startswith("with")):
		return pd.DataFrame(), "Only SELECT statements are allowed for safety."
	engine = getattr(db, "engine", None) or getattr(db, "_engine", None)
	if engine is not None:
		try:
			from pandas import read_sql_query
			with engine.connect() as conn:
				df = read_sql_query(sql, conn)
			return df, None
		except Exception as e:
			return pd.DataFrame(), str(e)
	return pd.DataFrame(), "SQLDatabase engine is not available in this version; use run_sqlite(db_path, sql)."


@traceable(name="sql.exec.sqlite")
def run_sqlite(db_path: str, sql: str) -> Tuple[pd.DataFrame, Optional[str]]:
	first_token = sql.strip().lower()
	if not (first_token.startswith("select") or first_token.startswith("with")):
		return pd.DataFrame(), "Only SELECT statements are allowed for safety."
	try:
		conn = sqlite3.connect(db_path)
		try:
			df = pd.read_sql_query(sql, conn)
			return df, None
		finally:
			conn.close()
	except Exception as e:
		return pd.DataFrame(), str(e)


@traceable(name="sql.exec.postgres")
def run_postgres(sql: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """Chạy SQL query trên PostgreSQL database"""
    first_token = sql.strip().lower()
    if not (first_token.startswith("select") or first_token.startswith("with")):
        return pd.DataFrame(), "Only SELECT statements are allowed for safety."
    
    try:
        # Sử dụng SQLAlchemy thay vì psycopg2 trực tiếp
        from sqlalchemy import create_engine
        engine = create_engine("postgresql://inventory_user:inventory_pass@localhost:5432/inventory_db")
        df = pd.read_sql_query(sql, engine)
        return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)


def run_sql_unified(sql: str, db_type: str = "postgresql") -> Tuple[pd.DataFrame, Optional[str]]:
	"""Chạy SQL query trên database được chỉ định"""
	if db_type.lower() == "postgresql":
		return run_postgres(sql)
	else:
		return run_sqlite("data/inventory.db", sql)
