from core.database import get_db_connection

def upgrade_database():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # --- อัปเกรดระบบสินค้า (Products) ---
            # เพิ่มฟิลด์ประเภทการคิดคอมมิชชัน: 'price' (ร้อยละจากราคา), 'net_profit' (กำไรหลังหักต้นทุน/ภาษี)
            # เพิ่มฟิลด์แต้มที่ทศนิยมลึก 4 ตำแหน่ง DECIMAL(10, 4) รองรับ 0.001 แต้ม
            cursor.execute("ALTER TABLE products ADD COLUMN comm_calc_type ENUM('price', 'net_profit', 'flat_rate') DEFAULT 'price'")
            cursor.execute("ALTER TABLE products ADD COLUMN net_profit_base DECIMAL(10, 2) DEFAULT 0.00")
            cursor.execute("ALTER TABLE products ADD COLUMN extra_point_reward DECIMAL(10, 4) DEFAULT 0.0000") # แต้มเศษสตางค์
            cursor.execute("ALTER TABLE products ADD COLUMN supplier_sku VARCHAR(100) DEFAULT NULL")
            
            # --- อัปเกรดระบบถอนเงิน (Withdrawals) ---
            # เพิ่มช่องทางการถอน: โอนผ่านธนาคาร หรือ นัดรับเงินสดที่สาขา
            cursor.execute("ALTER TABLE withdrawals ADD COLUMN withdrawal_method ENUM('bank_transfer', 'branch_cash') DEFAULT 'bank_transfer'")
            cursor.execute("ALTER TABLE withdrawals ADD COLUMN branch_id VARCHAR(50) DEFAULT NULL")
            cursor.execute("ALTER TABLE withdrawals ADD COLUMN appointment_datetime DATETIME DEFAULT NULL") # ระบบนัดหมายเตรียมเงิน
            cursor.execute("ALTER TABLE withdrawals ADD COLUMN cash_handling_fee DECIMAL(10, 2) DEFAULT 0.00") # ค่าธรรมเนียมบริษัท
            cursor.execute("ALTER TABLE withdrawals ADD COLUMN bonus_points_reward DECIMAL(10, 2) DEFAULT 0.00") # แต้มแถมให้ถ้ารับเงินสด
            
        conn.commit()
        print("✅ Advanced Database Upgraded! รองรับ 0.001 แต้ม, คิดคอมแบบ Net Profit และระบบนัดรับเงินสดสาขาเรียบร้อย!")
    except Exception as e:
        print(f"⚠️ Warning (อาจอัปเกรดไปแล้ว): {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_database()
