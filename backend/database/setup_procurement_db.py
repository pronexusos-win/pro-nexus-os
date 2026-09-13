from core.database import get_db_connection

def setup_procurement():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตารางซัพพลายเออร์ (Supplier Master)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                supplier_name VARCHAR(255),
                contact_info TEXT,
                credit_term INT DEFAULT 0 -- เครดิตเทอมกี่วัน
            )
            """)
            
            # ตารางหัวบิลใบสั่งซื้อ (Purchase Order)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                po_number VARCHAR(50) UNIQUE,
                supplier_id INT,
                status INT DEFAULT 0, -- 0=รออนุมัติ, 1=สั่งแล้ว, 2=รับบางส่วน, 9=รับครบ, 99=ยกเลิก
                total_amount DECIMAL(10,2) DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # ตารางรายการสินค้าใน PO (PO Items)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS po_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                po_id INT,
                sku VARCHAR(100),
                order_qty INT DEFAULT 0,
                received_qty INT DEFAULT 0, -- ยอดที่รับเข้าจริง
                unit_price DECIMAL(10,2) DEFAULT 0.0
            )
            """)
            
            # ตารางเอกสารรับของเข้าคลัง (Goods Receipt - GR)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS goods_receipts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                gr_number VARCHAR(50) UNIQUE,
                po_id INT,
                receive_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                receiver_id VARCHAR(50) -- พนักงานที่รับของ
            )
            """)
        conn.commit()
        print("✅ Procurement (PO, GR, Supplier) tables created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_procurement()
