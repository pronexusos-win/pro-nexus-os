from core.database import get_db_connection

def update_schema_for_offline():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # เพิ่มคอลัมน์ offline_tx_id และตั้งเป็น UNIQUE Index
            cursor.execute("""
            ALTER TABLE sales_documents 
            ADD COLUMN IF NOT EXISTS offline_tx_id VARCHAR(50) NULL,
            ADD UNIQUE INDEX idx_offline_tx (offline_tx_id);
            """)
        conn.commit()
        print("✅ Added offline_tx_id to sales_documents table to prevent duplicate syncing!")
    except Exception as e:
        print(f"Schema notice: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_schema_for_offline()
