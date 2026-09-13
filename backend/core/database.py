import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("MYSQLHOST", "localhost"),
        user=os.getenv("MYSQLUSER", "root"),
        password=os.getenv("MYSQLPASSWORD", "llBjwNgLhwTpUhHgeLuXZNkOOdbppjOn"),
        database=os.getenv("MYSQLDATABASE", "railway"),
        port=int(os.getenv("MYSQLPORT", 3306)),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )