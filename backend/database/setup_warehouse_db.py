from core.database import get_db_connection

def setup_warehouse():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS warehouse_inventory (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                sku VARCHAR(100),
                product_name VARCHAR(255),
                warehouse_zone VARCHAR(100),
                stock_quantity INT DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_tenant_sku (tenant_id, sku)
            )
            """)
        conn.commit()
        print("✅ Warehouse Inventory & SKU Barcode table created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_warehouse()
