from core.database import get_db_connection

def setup_promotions():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตารางเก็บเงื่อนไขโปรโมชัน
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS promotions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                promo_code VARCHAR(50) UNIQUE, -- เช่น NEWYEAR10, MINUS50
                promo_name VARCHAR(255),
                discount_type VARCHAR(20), -- 'percent' (ลด %), 'amount' (ลดเป็นบาท)
                discount_value DECIMAL(10,2), -- มูลค่าส่วนลด เช่น 10(%), 50(บาท)
                apply_level VARCHAR(20), -- 'bill' (ลดท้ายบิล), 'item' (ลดเฉพาะสินค้า)
                target_sku VARCHAR(100) NULL, -- ระบุ SKU ถ้ารถเฉพาะชิ้น
                min_purchase_amount DECIMAL(10,2) DEFAULT 0.0, -- ยอดซื้อขั้นต่ำ
                start_date DATETIME,
                end_date DATETIME,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # ใส่ข้อมูลโปรโมชันตัวอย่าง (Mock Data)
            cursor.execute("""
            INSERT IGNORE INTO promotions (tenant_id, promo_code, promo_name, discount_type, discount_value, apply_level, min_purchase_amount, start_date, end_date)
            VALUES 
            ('default', 'WELCOME50', 'ส่วนลดลูกค้าใหม่ 50 บาท', 'amount', 50.00, 'bill', 200.00, '2026-01-01', '2026-12-31'),
            ('default', 'MEGA10', 'ลด 10% ท้ายบิล', 'percent', 10.00, 'bill', 1000.00, '2026-01-01', '2026-12-31')
            """)
        conn.commit()
        print("✅ Promotions table created and seeded successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_promotions()
