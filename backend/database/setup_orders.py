from core.database import get_db_connection

def setup_orders():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id VARCHAR(50) PRIMARY KEY,
                tenant_id VARCHAR(50),
                member_id VARCHAR(50),
                product_id VARCHAR(50),
                total_amount DECIMAL(10, 2),
                tracking_no VARCHAR(100) DEFAULT NULL,
                courier VARCHAR(50) DEFAULT NULL,
                status ENUM('pending', 'paid', 'shipped', 'delivered') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        conn.commit()
        print("✅ Orders & Logistics database setup completed!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_orders()
