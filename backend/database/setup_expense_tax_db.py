from core.database import get_db_connection

def setup_expense_tax():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS expense_transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                doc_no VARCHAR(50) UNIQUE,
                category VARCHAR(50), -- Auto-categorized
                description TEXT,
                subtotal DECIMAL(10,2), -- ยอดก่อนภาษี
                vat_amount DECIMAL(10,2) DEFAULT 0.0, -- VAT 7%
                wht_amount DECIMAL(10,2) DEFAULT 0.0, -- หัก ณ ที่จ่าย (เช่น 3%)
                net_paid DECIMAL(10,2), -- ยอดที่จ่ายเงินออกไปจริง
                payee_name VARCHAR(255),
                payee_tax_id VARCHAR(20), -- เลขผู้เสียภาษี (สำหรับออก 50 ทวิ)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        conn.commit()
        print("✅ Expense and Tax Tracking table created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_expense_tax()
