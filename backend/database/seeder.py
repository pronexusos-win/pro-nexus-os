from core.database import get_db_connection
from services.auth.auth_engine import get_pin_hash

def seed_data():
    conn = get_db_connection()
    default_pin_hash = get_pin_hash("123456")
    
    try:
        with conn.cursor() as cursor:
            # 1. สร้าง Tenant ทั้ง 3 บริษัท
            tenants = [
                ("tenant_tp_extra", "TP Extra System"),
                ("tenant_luckio", "Luckio Platform"),
                ("tenant_peak_icon", "Peak Icon")
            ]
            for t in tenants:
                cursor.execute("INSERT IGNORE INTO tenants (tenant_id, name) VALUES (%s, %s)", t)
            
            # 2. จำลอง User ให้บริษัท TP Extra (มีสายงาน 4 ชั้น)
            tp_users = [
                ("tp_001", "tenant_tp_extra", None, "คุณ เอ (TP)", "company_admin", "line_tp_a", default_pin_hash),
                ("tp_002", "tenant_tp_extra", "tp_001", "คุณ บี (TP)", "franchise", "line_tp_b", default_pin_hash),
                ("tp_003", "tenant_tp_extra", "tp_002", "คุณ ซี (TP)", "member", "line_tp_c", default_pin_hash),
                ("tp_004", "tenant_tp_extra", "tp_003", "คุณ ดี (TP)", "member", "line_tp_d", default_pin_hash)
            ]
            
            # 3. จำลอง User ให้บริษัท Luckio (ชั้นเดียว) และ Peak Icon
            other_users = [
                ("luck_001", "tenant_luckio", None, "คุณ เอก (Luckio)", "company_admin", "line_luck_a", default_pin_hash),
                ("luck_002", "tenant_luckio", "luck_001", "คุณ ทู (Luckio)", "member", "line_luck_b", default_pin_hash),
                ("peak_001", "tenant_peak_icon", None, "คุณ พีค (Peak)", "company_admin", "line_peak_a", default_pin_hash)
            ]
            
            for u in tp_users + other_users:
                cursor.execute("""
                    INSERT INTO members (member_id, tenant_id, sponsor_id, name, role, line_user_id, pin_hash) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE line_user_id=VALUES(line_user_id), pin_hash=VALUES(pin_hash)
                """, u)
            
        conn.commit()
        print("\n✅ Database Seeded! สร้าง 3 บริษัท (TP Extra, Luckio, Peak Icon) พร้อม User จำลองเรียบร้อย")
    except Exception as e:
        print(f"\n❌ Seeding Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_data()
