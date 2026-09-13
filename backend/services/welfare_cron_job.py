from core.database import get_db_connection
from datetime import datetime

def process_end_of_month_welfare():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. เช็กยอดเงินกองทุนรวม
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) AS total_fund 
                FROM wallet_transactions 
                WHERE trans_type = 'WELFARE_FUND_IN' 
                AND MONTH(created_at) = MONTH(CURRENT_DATE())
            """)
            fund_data = cursor.fetchone()
            total_fund = float(fund_data['total_fund'])
            
            if total_fund <= 0:
                print("ไม่มีเงินในกองทุนสวัสดิการเดือนนี้")
                return

            # 2. ค้นหาสมาชิกปลายสาย (ไม่มีลูกทีม) & ยอดซื้อสะสม >= 500
            cursor.execute("""
                SELECT tree.user_id 
                FROM tpx_unilevel_tree tree
                JOIN (
                    SELECT buyer_id, SUM(total_sales_amount) as spent 
                    FROM sales_transactions 
                    WHERE MONTH(created_at) = MONTH(CURRENT_DATE()) 
                    GROUP BY buyer_id
                ) sales ON tree.user_id = sales.buyer_id
                WHERE sales.spent >= 500
                AND tree.user_id NOT IN (
                    SELECT sponsor_id FROM tpx_unilevel_tree WHERE sponsor_id IS NOT NULL
                )
            """)
            eligible_users = cursor.fetchall()
            user_count = len(eligible_users)
            
            if user_count == 0:
                print("ไม่มีสมาชิกเข้าเงื่อนไขรับกองทุน เงินตกเป็นของบริษัท")
                return
                
            # 3. คำนวณยอดและบังคับเพดาน 1,000 แต้ม
            point_per_person = total_fund / user_count
            if point_per_person > 1000:
                point_per_person = 1000.00
                
            # 4. จ่ายแต้มและบันทึกวันหมดอายุ
            for user in eligible_users:
                cursor.execute("""
                    UPDATE tpx_wallets 
                    SET shopping_point = shopping_point + %s 
                    WHERE user_id = %s
                """, (point_per_person, user['user_id']))
                
                cursor.execute("""
                    INSERT INTO wallet_transactions 
                    (tenant_id, user_id, trans_type, direction, amount, note, expiry_date)
                    VALUES ('tp_extra', %s, 'WELFARE_PAYOUT', 'IN', %s, 'กองทุนปลายสาย (หมดอายุสิ้นเดือนหน้า)', LAST_DAY(CURRENT_DATE() + INTERVAL 1 MONTH))
                """, (user['user_id'], point_per_person))
                
        conn.commit()
        print(f"✅ แจกจ่ายกองทุนสำเร็จ: {user_count} คน คนละ {point_per_person:,.2f} แต้ม")
    finally:
        conn.close()

if __name__ == "__main__":
    process_end_of_month_welfare()
