import os
import sqlite3
import pandas as pd
from typing import Tuple, Optional

from langchain_community.utilities import SQLDatabase

from utils.logger import traceable


def get_sqlalchemy_url(sqlite_path: str) -> str:
	abs_path = os.path.abspath(sqlite_path)
	return f"sqlite:///{abs_path}"


def get_db(sqlite_path: str) -> SQLDatabase:
	url = get_sqlalchemy_url(sqlite_path)
	return SQLDatabase.from_uri(url)


@traceable(name="sql.exec")
def run_sql(db: SQLDatabase, sql: str) -> Tuple[pd.DataFrame, Optional[str]]:
	if not sql.strip().lower().startswith("select"):
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
	if not sql.strip().lower().startswith("select"):
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
