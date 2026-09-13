from core.database import get_db_connection

def setup_pos():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตารางเก็บข้อมูลบาร์โค้ดและซ่อนต้นทุน
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_inventory (
                barcode VARCHAR(100) PRIMARY KEY,
                tenant_id VARCHAR(50),
                product_id VARCHAR(50),
                product_name VARCHAR(255),
                retail_price DECIMAL(10, 2),
                cost_price DECIMAL(10, 2), -- ซ่อนไว้ให้เฉพาะผู้บริหารเห็น
                stock_qty INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # จำลองสินค้าในร้านค้า
            sample_items = [
                ("8850012345671", "tenant_tp_extra", "prod_tp_001", "กาแฟ TP Extra", 100.00, 40.00, 150),
                ("8850012345672", "tenant_luckio", "prod_luck_001", "กล่องสุ่ม Luckio", 500.00, 200.00, 80),
                ("8850012345673", "tenant_peak_icon", "prod_peak_001", "กล่องพัสดุ Peak Size M", 750.00, 300.00, 50)
            ]
            
            for item in sample_items:
                cursor.execute("""
                    INSERT IGNORE INTO store_inventory (barcode, tenant_id, product_id, product_name, retail_price, cost_price, stock_qty)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, item)
                
        conn.commit()
        print("✅ POS Store database & Barcode system setup completed!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_pos()
