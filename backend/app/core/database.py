import os
import pymysql
from dbutils.pooled_db import PooledDB
from contextlib import contextmanager
import logging

logger = logging.getLogger("db_pool")
_pool = None

def get_db_pool():
    global _pool
    if _pool is None:
        db_host = os.getenv("MYSQLHOST") or os.getenv("DB_HOST") or "127.0.0.1"
        db_user = os.getenv("MYSQLUSER") or os.getenv("DB_USER") or "root"
        db_pass = os.getenv("MYSQLPASSWORD") or os.getenv("DB_PASSWORD") or ""
        db_name = os.getenv("MYSQLDATABASE") or os.getenv("DB_NAME") or "railway"
        db_port = int(os.getenv("MYSQLPORT") or os.getenv("DB_PORT") or 3306)

        try:
            _pool = PooledDB(
                creator=pymysql,
                mincached=0,  # หัวใจสำคัญ: ไม่ต่อ DB จนกว่าจะมีการเรียกใช้งานจริง
                maxcached=10,
                maxconnections=20,
                blocking=True,
                host=db_host,
                user=db_user,
                password=db_pass,
                database=db_name,
                port=db_port,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
        except Exception as e:
            logger.error(f"DB Error: {e}")
            raise
    return _pool

@contextmanager
def get_db_connection():
    pool = get_db_pool()
    conn = pool.connection()
    try:
        yield conn
    finally:
        conn.close()
