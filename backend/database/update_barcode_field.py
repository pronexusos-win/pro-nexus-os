from core.database import get_db_connection

def update_barcode():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            ALTER TABLE products 
            ADD COLUMN IF NOT EXISTS barcode VARCHAR(100) NULL,
            ADD INDEX idx_barcode (barcode);
            """)
        conn.commit()
        print("✅ Added barcode column and index to products table!")
    except Exception as e:
        print(f"Notice: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_barcode()
