from core.database import get_db_connection

def setup_sales_docs():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตารางหัวเอกสารงานขาย (Header)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_documents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tenant_id VARCHAR(50),
                doc_no VARCHAR(50) UNIQUE,
                doc_type VARCHAR(10), -- QT (เสนอราคา), INV (กำกับภาษี/ใบเสร็จ), CN (ลดหนี้)
                customer_id VARCHAR(50) NULL,
                customer_name VARCHAR(255),
                customer_tax_id VARCHAR(20) NULL, -- เลขประจำตัวผู้เสียภาษี 13 หลัก
                customer_address TEXT NULL,
                customer_branch VARCHAR(50) DEFAULT 'สำนักงานใหญ่',
                subtotal DECIMAL(10,2) DEFAULT 0.0,
                vat_amount DECIMAL(10,2) DEFAULT 0.0,
                grand_total DECIMAL(10,2) DEFAULT 0.0,
                status VARCHAR(20) DEFAULT 'draft', -- draft, issued, cancelled
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # ตารางรายการสินค้าในเอกสาร (Lines)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_document_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                doc_id INT,
                sku VARCHAR(100),
                product_name VARCHAR(255),
                quantity INT,
                unit_price DECIMAL(10,2),
                discount_amount DECIMAL(10,2) DEFAULT 0.0,
                total_price DECIMAL(10,2)
            )
            """)
        conn.commit()
        print("✅ Sales Documents & Tax Invoice tables created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_sales_docs()
