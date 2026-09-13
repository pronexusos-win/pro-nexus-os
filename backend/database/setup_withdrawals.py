from core.database import get_db_connection

def setup_withdrawals():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                withdrawal_id VARCHAR(50) PRIMARY KEY,
                tenant_id VARCHAR(50),
                member_id VARCHAR(50),
                amount DECIMAL(10, 2),
                bank_name VARCHAR(100),
                bank_account_no VARCHAR(50),
                bank_account_name VARCHAR(100),
                status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
                admin_id VARCHAR(50) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """)
        conn.commit()
        print("✅ Withdrawals database setup completed!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_withdrawals()
