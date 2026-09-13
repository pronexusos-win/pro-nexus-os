from core.database import get_db_connection

def setup_community():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตารางกระดานข่าวชุมชน
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS community_posts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                author_id VARCHAR(50),
                post_type VARCHAR(20),
                title VARCHAR(255),
                details TEXT,
                price DECIMAL(10,2) DEFAULT 0.0,
                status VARCHAR(20) DEFAULT 'active', -- active, in_progress, completed, cancelled
                matched_with VARCHAR(50) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # ตารางสต็อกบนรถเร่ (แยกจากสต็อกคลังใหญ่)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS mobile_vendor_inventory (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                vendor_id VARCHAR(50),
                sku VARCHAR(100),
                stock_quantity INT DEFAULT 0,
                UNIQUE KEY unique_vendor_sku (tenant_id, vendor_id, sku)
            )
            """)
            
            # ตารางการจองสินค้าล่วงหน้า
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pre_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                vendor_id VARCHAR(50),
                customer_id VARCHAR(50),
                sku VARCHAR(100),
                quantity INT,
                status VARCHAR(20) DEFAULT 'reserved', -- reserved, picked_up, cancelled
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        conn.commit()
        print("✅ Community Board & Pre-order tables created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_community()
