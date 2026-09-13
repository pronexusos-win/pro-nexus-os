from core.database import get_db_connection

def setup_tp_extra_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตารางผังองค์กร (ชี้ตัวผู้แนะนำตรง)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tpx_unilevel_tree (
                user_id VARCHAR(50) PRIMARY KEY,
                sponsor_id VARCHAR(50) NULL, -- ผู้แนะนำ (Upline ชั้นที่ 1)
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_sponsor (sponsor_id)
            )
            """)
            
            # ตารางกระเป๋าเงิน (แยก Cash / Shopping)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tpx_wallets (
                user_id VARCHAR(50) PRIMARY KEY,
                cash_point DECIMAL(10,2) DEFAULT 0.00, -- 80% (รอเงื่อนไขปลดล็อก 1,000)
                shopping_point DECIMAL(10,2) DEFAULT 0.00, -- 20% (ซื้อของเท่านั้น)
                rollover_cash_point DECIMAL(10,2) DEFAULT 0.00, -- แต้มทบยอดจากเดือนก่อนๆ
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """)
        conn.commit()
        print("✅ TP Extra Unilevel & Wallet tables created!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_tp_extra_db()
