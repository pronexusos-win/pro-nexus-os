import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.app.core.database import get_db_connection

DDL = """
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_slug ENUM('pro_nexus', 'tp_extra', 'luck_kio', 'peak_icon') NOT NULL DEFAULT 'tp_extra',
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    stock_quantity INT NOT NULL DEFAULT 0,
    image_url TEXT NULL,
    category VARCHAR(100) DEFAULT 'general',
    is_active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_company_active (company_slug, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

SAMPLE_PRODUCTS = [
    ("tp_extra", "ชุดสินค้าแบ่งปัน A (กาแฟเพื่อสุขภาพ)", "กาแฟอาราบิก้าเกรดพรีเมียม 1 กล่อง (10 ซอง)", 290.00, 100, "https://via.placeholder.com/300/06C755/FFFFFF?text=Coffee+Set+A", "beverage"),
    ("tp_extra", "ชุดสินค้าแบ่งปัน B (อาหารเสริมวิตามินรวม)", "วิตามินรวมเข้มข้นบำรุงสุขภาพ 30 แคปซูล", 490.00, 50, "https://via.placeholder.com/300/06C755/FFFFFF?text=Vitamin+Set+B", "supplement"),
    ("tp_extra", "เสื้อยืดสมาชิก TP Extra Exclusive", "เสื้อยืดผ้าคอนตอน 100% สกรีนโลโก้ TP Extra", 350.00, 80, "https://via.placeholder.com/300/06C755/FFFFFF?text=TP+T-Shirt", "merchandise")
]

def init_products():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(DDL)
            
            # เช็กว่ามีข้อมูลหรือยัง ถ้ายังไม่มีให้ใส่ mock data
            cursor.execute("SELECT COUNT(*) AS total FROM products WHERE company_slug = 'tp_extra';")
            count = cursor.fetchone()["total"]
            
            if count == 0:
                insert_sql = """
                    INSERT INTO products (company_slug, name, description, price, stock_quantity, image_url, category)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """
                cursor.executemany(insert_sql, SAMPLE_PRODUCTS)
                print("🛒 เพิ่มรายการสินค้าเริ่มต้นเรียบร้อยแล้ว!")
        conn.commit()
    print("✅ ตาราง products พร้อมใช้งาน!")

if __name__ == "__main__":
    init_products()
