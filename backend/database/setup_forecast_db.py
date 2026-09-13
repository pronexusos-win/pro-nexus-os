from core.database import get_db_connection

def setup_forecast_schema():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # เพิ่มฟิลด์ จุดสั่งซื้อ, ซัพพลายเออร์หลัก, และระยะเวลารอของ (Lead Time)
            cursor.execute("""
            ALTER TABLE products 
            ADD COLUMN IF NOT EXISTS reorder_point INT DEFAULT 10,
            ADD COLUMN IF NOT EXISTS safety_stock INT DEFAULT 5,
            ADD COLUMN IF NOT EXISTS lead_time_days INT DEFAULT 3,
            ADD COLUMN IF NOT EXISTS default_supplier_id INT NULL;
            """)
        conn.commit()
        print("✅ Added Auto-PO & Forecast fields to Products table!")
    except Exception as e:
        print(f"Schema update notice (might already exist): {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_forecast_schema()
