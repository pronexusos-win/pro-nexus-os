import os
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from contextlib import contextmanager
from typing import Generator

# อ่านค่าคอนฟิกจาก Railway Variables (หรือ Local .env)
# Railway มักให้มาเป็นตัวแปรแยก หรือเป็น MYSQL_URL
DB_HOST = os.getenv("MYSQLHOST", os.getenv("DB_HOST", "localhost"))
DB_USER = os.getenv("MYSQLUSER", os.getenv("DB_USER", "root"))
DB_PASSWORD = os.getenv("MYSQLPASSWORD", os.getenv("DB_PASSWORD", ""))
DB_PORT = int(os.getenv("MYSQLPORT", os.getenv("DB_PORT", 3306)))
DB_NAME = os.getenv("MYSQLDATABASE", os.getenv("DB_NAME", "railway"))

# สร้าง Connection Pool
pool = PooledDB(
    creator=pymysql,
    maxconnections=10,       # จำนวน connection สูงสุดใน pool
    mincached=2,             # จำนวน connection ขั้นต่ำที่เปิดทิ้งไว้
    maxcached=5,             # จำนวน idle connection สูงสุด
    maxshared=3,
    blocking=True,           # รอกรณี connection เต็มแทนที่จะ error
    maxusage=None,
    setsession=[],
    ping=1,                  # ตรวจสอบการเชื่อมต่อก่อนดึงมาใช้ (แก้ปัญหา timeout บน cloud)
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    charset="utf8mb4",
    cursorclass=DictCursor   # ให้ return ผลลัพธ์เป็น Dict เสมอ
)

@contextmanager
def get_db_connection() -> Generator[pymysql.connections.Connection, None, None]:
    """Context manager สำหรับดึง connection จาก pool และคืนให้อัตโนมัติ"""
    connection = pool.connection()
    try:
        yield connection
    finally:
        connection.close()  # เป็นการ return กลับเข้า pool ไม่ได้ปิดจริง
