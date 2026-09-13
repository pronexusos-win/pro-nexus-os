from core.database import get_db_connection

def setup_kiosk():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS kiosk_machines (
                kiosk_id VARCHAR(50) PRIMARY KEY,
                tenant_id VARCHAR(50),
                type VARCHAR(50), -- เช่น vending, massage_chair, water_dispenser
                status VARCHAR(20) DEFAULT 'online', -- online, offline, maintenance
                location_name TEXT,
                last_ping TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS kiosk_inventory (
                id INT AUTO_INCREMENT PRIMARY KEY,
                kiosk_id VARCHAR(50),
                sku VARCHAR(50),
                product_name VARCHAR(100),
                price DECIMAL(10,2),
                stock_quantity INT DEFAULT 0,
                slot_number VARCHAR(10), -- เช่น A1, B2 (ช่องสปริงในตู้)
                UNIQUE KEY unique_slot (kiosk_id, slot_number)
            )
            """)
        conn.commit()
        print("✅ IoT Kiosk tables created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_kiosk()
