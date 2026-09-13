from core.database import get_db_connection

def update_pricing_schema():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # เพิ่มคอลัมน์สำหรับราคา 8 ระดับ (ตัวอย่าง 3 ระดับก่อน) และ MOQ ในตาราง products
            cursor.execute("""
            ALTER TABLE products 
            ADD COLUMN IF NOT EXISTS price_wholesale_1 DECIMAL(10,2) DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS moq_wholesale_1 INT DEFAULT 10,
            ADD COLUMN IF NOT EXISTS price_wholesale_2 DECIMAL(10,2) DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS moq_wholesale_2 INT DEFAULT 50;
            """)
        conn.commit()
        print("✅ Added Wholesale Pricing & MOQ to Products table!")
    finally:
        conn.close()

if __name__ == "__main__":
    update_pricing_schema()
