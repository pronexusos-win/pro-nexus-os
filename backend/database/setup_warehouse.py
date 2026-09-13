from core.database import get_db_connection

def setup_inventory():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id VARCHAR(50) PRIMARY KEY,
                tenant_id VARCHAR(50),
                sku VARCHAR(50) UNIQUE,
                name VARCHAR(255),
                price DECIMAL(10, 2),
                stock INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # จำลองสินค้าเข้าคลังรอไว้เลย!
            sample_products = [
                ("prod_tp_001", "tenant_tp_extra", "TP-COFFEE-01", "กาแฟ TP Extra (แพ็ค 10)", 1000.00, 500),
                ("prod_luck_001", "tenant_luckio", "LUCK-BOX-01", "กล่องสุ่ม Luckio Box", 500.00, 1000),
                ("prod_peak_001", "tenant_peak_icon", "PEAK-BOX-M", "กล่องพัสดุ Peak Size M (100 ใบ)", 750.00, 200)
            ]
            
            for p in sample_products:
                cursor.execute("""
                    INSERT IGNORE INTO products (product_id, tenant_id, sku, name, price, stock) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, p)
                
        conn.commit()
        print("✅ Warehouse & Products database setup completed!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_inventory()
