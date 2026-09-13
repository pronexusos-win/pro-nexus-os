from core.database import get_db_connection

def setup_advanced_inventory():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 3.3 เพิ่มประเภทภาษี (VAT/NON_VAT) และต้นทุนเฉลี่ย (MAC) ลงในตารางสินค้า
            cursor.execute("""
            ALTER TABLE products 
            ADD COLUMN IF NOT EXISTS tax_type VARCHAR(20) DEFAULT 'VAT', -- 'VAT' หรือ 'NON_VAT'
            ADD COLUMN IF NOT EXISTS moving_avg_cost DECIMAL(10,4) DEFAULT 0.0;
            """)
            
            # 3.4 ตารางเก็บข้อมูลล็อตสินค้า (Lot Tracking)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_lots (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                sku VARCHAR(100),
                lot_number VARCHAR(50),
                cost_price DECIMAL(10,4), -- ราคาทุนของล็อตนี้
                quantity INT DEFAULT 0, -- จำนวนที่เหลือในล็อตนี้
                mfg_date DATE NULL, -- วันผลิต
                exp_date DATE NULL, -- วันหมดอายุ
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_tenant_sku_lot (tenant_id, sku, lot_number)
            )
            """)
        conn.commit()
        print("✅ Advanced Inventory (VAT, Moving Avg, Lot Tracking) created successfully!")
    except Exception as e:
        print(f"Schema notice: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_advanced_inventory()
