from core.database import get_db_connection

def setup_fulfillment():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตารางออเดอร์จัดส่ง (แยกจากบิล POS ปกติ)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS fulfillment_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                order_ref VARCHAR(50), -- อ้างอิงเลขบิลขาย
                tracking_no VARCHAR(100) UNIQUE, -- เลขพัสดุ
                customer_name VARCHAR(255),
                shipping_address TEXT,
                status VARCHAR(20) DEFAULT 'pending', -- pending, packing, packed, shipped
                packer_id VARCHAR(50) NULL, -- พนักงานที่แพ็ค
                packed_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # ตารางรายการสินค้าที่ต้องแพ็ค
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS fulfillment_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT,
                sku VARCHAR(100),
                required_qty INT, -- จำนวนที่ลูกค้าสั่ง
                packed_qty INT DEFAULT 0 -- จำนวนที่สแกนลงกล่องแล้ว
            )
            """)
        conn.commit()
        print("✅ Fulfillment (Scan-to-Pack) tables created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_fulfillment()
