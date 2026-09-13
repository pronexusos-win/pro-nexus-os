from core.database import get_db_connection

def setup_logistics():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตารางจัดการออเดอร์เดลิเวอรี่
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                order_ref VARCHAR(50), -- อ้างอิงเลขบิลขาย (INV)
                customer_name VARCHAR(255),
                customer_phone VARCHAR(20),
                delivery_address TEXT,
                latitude DECIMAL(10,8) NULL,
                longitude DECIMAL(10,8) NULL,
                delivery_fee DECIMAL(10,2) DEFAULT 0.0,
                provider VARCHAR(50) DEFAULT 'in_house', -- in_house, lalamove, grab
                rider_id VARCHAR(50) NULL, -- รหัสคนขับ (ถ้าเป็น in_house)
                rider_name VARCHAR(100) NULL,
                tracking_url TEXT NULL, -- ลิงก์ติดตามสถานะของ 3rd Party
                status VARCHAR(20) DEFAULT 'finding_rider', -- finding_rider, accepted, picked_up, on_the_way, delivered, cancelled
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """)
            
            # ตารางทะเบียนคนขับ (In-house Riders)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rider_profiles (
                rider_id VARCHAR(50) PRIMARY KEY,
                tenant_id VARCHAR(50),
                full_name VARCHAR(100),
                phone VARCHAR(20),
                vehicle_plate VARCHAR(20),
                status VARCHAR(20) DEFAULT 'offline', -- online, offline, busy
                current_lat DECIMAL(10,8) NULL,
                current_lng DECIMAL(10,8) NULL
            )
            """)
        conn.commit()
        print("✅ Logistics & Delivery tables created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_logistics()
