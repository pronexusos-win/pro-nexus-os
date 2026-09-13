from core.database import get_db_connection

def setup_restaurant_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตารางเก็บออเดอร์ร้านอาหาร (4 จอ)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS restaurant_orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                table_number VARCHAR(20),
                items TEXT,
                status VARCHAR(30) DEFAULT 'pending_kitchen',
                customer_id VARCHAR(50) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # ตารางรีวิวและให้ดาวสินค้า/ร้านค้า
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_reviews (
                review_id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                product_id VARCHAR(50),
                customer_id VARCHAR(50),
                rating INT CHECK (rating BETWEEN 1 AND 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
        conn.commit()
        print("✅ Restaurant & Offline POS database tables created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_restaurant_db()
