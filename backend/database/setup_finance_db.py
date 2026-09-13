from core.database import get_db_connection

def setup_finance():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. ตารางลูกหนี้การค้า (Accounts Receivable - AR)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts_receivable (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                customer_id VARCHAR(50),
                doc_ref VARCHAR(50), -- อ้างอิงเลขบิลขาย (INV)
                total_amount DECIMAL(10,2),
                paid_amount DECIMAL(10,2) DEFAULT 0.0,
                due_date DATE,
                status VARCHAR(20) DEFAULT 'pending', -- pending, partial, paid
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 2. ตารางเจ้าหนี้การค้า (Accounts Payable - AP)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts_payable (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                supplier_id INT,
                doc_ref VARCHAR(50), -- อ้างอิงเลขบิลรับของ (GR/PO)
                total_amount DECIMAL(10,2),
                paid_amount DECIMAL(10,2) DEFAULT 0.0,
                due_date DATE,
                status VARCHAR(20) DEFAULT 'pending', -- pending, partial, paid
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 3. สมุดรายวันรับ-จ่าย (General Ledger / Cash Book)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cash_book (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                trans_date DATE,
                trans_type VARCHAR(10), -- 'IN' (รายรับ), 'OUT' (รายจ่าย)
                category VARCHAR(50), -- เช่น SALES, AP_PAYMENT, AR_RECEIPT, OPEX
                amount DECIMAL(10,2),
                description TEXT,
                ref_doc VARCHAR(50) NULL, -- อ้างอิงเอกสาร
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        conn.commit()
        print("✅ Finance & Accounting tables (AP, AR, Cash Book) created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_finance()
