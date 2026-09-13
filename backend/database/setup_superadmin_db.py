from core.database import get_db_connection

def setup_superadmin():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตารางเก็บกติกาแบบ Dynamic (ให้ Super Admin ปรับเปลี่ยนได้ตลอดเวลา)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_configurations (
                tenant_id VARCHAR(50) PRIMARY KEY,
                is_system_active BOOLEAN DEFAULT TRUE, -- ปุ่มฉุกเฉินสำหรับปิดระบบชั่วคราว
                cash_point_ratio DECIMAL(5,2) DEFAULT 80.00, -- สัดส่วนกระเป๋าเงินสด
                shop_point_ratio DECIMAL(5,2) DEFAULT 20.00, -- สัดส่วนกระเป๋าช้อปปิ้ง
                welfare_fund_deduction DECIMAL(5,2) DEFAULT 10.00, -- หักเข้ากองทุนปลายสายกี่ %
                min_purchase_for_welfare DECIMAL(10,2) DEFAULT 500.00, -- ยอดซื้อขั้นต่ำรับสวัสดิการ
                max_welfare_cap DECIMAL(10,2) DEFAULT 1000.00, -- เพดานแต้มสวัสดิการต่อคน
                cash_withdrawal_min DECIMAL(10,2) DEFAULT 1000.00, -- ยอดปลดล็อกถอนเงินสด
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                updated_by VARCHAR(50) -- รหัส Super Admin ที่เข้ามาแก้ไขล่าสุด
            )
            """)
            
            # ใส่ค่า Default ให้ TP Extra
            cursor.execute("""
            INSERT IGNORE INTO tenant_configurations 
            (tenant_id, cash_point_ratio, shop_point_ratio, welfare_fund_deduction, min_purchase_for_welfare)
            VALUES ('tp_extra', 80.00, 20.00, 10.00, 500.00)
            """)
        conn.commit()
        print("✅ Super Admin Configuration tables created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_superadmin()
