from core.database import get_db_connection

def setup_cellpage():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cell_pages (
                tenant_id VARCHAR(50) PRIMARY KEY,
                store_name VARCHAR(255),
                slug VARCHAR(100) UNIQUE, -- ชื่อลิงก์ url เช่น /shop/pa-sri
                description TEXT,
                cover_image_url TEXT,
                theme_color VARCHAR(20) DEFAULT '#FF5733',
                is_open BOOLEAN DEFAULT TRUE,
                accepts_online_orders BOOLEAN DEFAULT TRUE,
                latitude DECIMAL(10,8),
                longitude DECIMAL(10,8),
                google_maps_url TEXT,
                rating DECIMAL(3,2) DEFAULT 0.0,
                review_count INT DEFAULT 0
            )
            """)
            
            # ตารางสร้าง QR Code แบบ Dynamic ราคาแปรผัน
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dynamic_qr_codes (
                id VARCHAR(50) PRIMARY KEY,
                tenant_id VARCHAR(50),
                action_type VARCHAR(20), -- 'payment', 'menu_view', 'booking'
                amount DECIMAL(10,2) NULL, -- ยอดเงิน (ถ้ามี)
                expires_at DATETIME,
                is_used BOOLEAN DEFAULT FALSE
            )
            """)
        conn.commit()
        print("✅ Cell Page Marketplace & Dynamic QR tables created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_cellpage()
