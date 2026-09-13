from core.database import get_db_connection

def setup_bom_schema():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตาราง Product BOM (สูตรส่วนผสม)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_bom (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                parent_sku VARCHAR(100), -- SKU ของสินค้าชุด หรือ เมนูอาหาร
                component_sku VARCHAR(100), -- SKU ของวัตถุดิบ หรือ สินค้าย่อย
                quantity DECIMAL(10,4), -- จำนวนที่ต้องใช้ (รองรับจุดทศนิยม เช่น 0.5 กก.)
                unit VARCHAR(50), -- หน่วยนับ (เช่น กรัม, ชิ้น, กิโลกรัม)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_bom_item (tenant_id, parent_sku, component_sku)
            )
            """)
        conn.commit()
        print("✅ Product BOM (Bill of Materials) table created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_bom_schema()
