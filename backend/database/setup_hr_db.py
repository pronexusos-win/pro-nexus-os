from core.database import get_db_connection

def setup_hr():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 6.1 ตารางจัดการกะ (Shift Handover)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pos_shifts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                pos_machine_id VARCHAR(50),
                cashier_id VARCHAR(50),
                opened_at DATETIME,
                closed_at DATETIME NULL,
                starting_cash DECIMAL(10,2) DEFAULT 0.0, -- เงินทอนตั้งต้น
                expected_cash DECIMAL(10,2) DEFAULT 0.0, -- ยอดเงินที่ควรมี (ซ่อนไม่ให้แคชเชียร์เห็น)
                actual_counted_cash DECIMAL(10,2) NULL, -- ยอดเงินที่แคชเชียร์นับได้จริงตอนปิดกะ
                discrepancy DECIMAL(10,2) NULL, -- ส่วนต่าง (เงินขาด/เงินเกิน)
                status VARCHAR(20) DEFAULT 'open' -- open, closed
            )
            """)
            
            # 6.3 ตารางเก็บประวัติคอมมิชชันรายบุคคล
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_commissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                employee_id VARCHAR(50),
                doc_no VARCHAR(50), -- อ้างอิงเลขบิลขาย
                sku VARCHAR(100),
                sale_amount DECIMAL(10,2), -- ยอดขายชิ้นนั้น
                commission_earned DECIMAL(10,2), -- ค่าคอมที่ได้
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        conn.commit()
        print("✅ HR tables (Shifts & Commissions) created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_hr()
