from datetime import datetime, timedelta
from backend.app.core.database import get_db_connection

def calculate_and_save_order_split(order_no: str, total_amount: float, company_slug: str = "tp_extra"):
    """
    คำนวณตัดแบ่งเงิน พร้อมคำนวณเวลาตั้งสิทธิ์คอมมิชชัน (Commission Settlement Window)
    """
    total = float(total_amount)
    cost = round(total * 0.60, 2)
    shop_fee = round(total * 0.10, 2)
    member_points = round(total * 0.05, 2)
    net_profit = round(total - (cost + shop_fee + member_points), 2)

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # ตรวจหาระยะเวลารอตั้งสิทธิ์สูงสุดของสินค้าในบิลนี้
            cursor.execute(
                """
                SELECT COALESCE(MAX(p.settlement_days), 3) as max_days
                FROM order_items oi
                JOIN products p ON oi.sku = p.sku AND p.company_slug = %s
                WHERE oi.order_no = %s;
                """,
                (company_slug, order_no)
            )
            row = cursor.fetchone()
            settlement_days = row["max_days"] if row and row["max_days"] is not None else 3

            now = datetime.now()
            settle_due_at = now + timedelta(days=settlement_days)
            
            # ถ้าสินค้าตั้งสิทธิ์ 0 วัน (เช่น ของกิน หรือซื้อหน้าร้านจบเลย) ให้ settled ทันที
            initial_status = "settled" if settlement_days == 0 else "unsettled"

            insert_sql = """
                INSERT INTO order_splits (
                    order_no, company_slug, total_amount, 
                    cost_amount, shop_fee, member_points_cashback, net_profit,
                    commission_status, settle_due_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    total_amount = VALUES(total_amount),
                    cost_amount = VALUES(cost_amount),
                    shop_fee = VALUES(shop_fee),
                    member_points_cashback = VALUES(member_points_cashback),
                    net_profit = VALUES(net_profit),
                    commission_status = VALUES(commission_status),
                    settle_due_at = VALUES(settle_due_at);
            """

            cursor.execute(insert_sql, (
                order_no, company_slug, total,
                cost, shop_fee, member_points, net_profit,
                initial_status, settle_due_at
            ))
        conn.commit()

    print(f"✅ บันทึกคอมมิชชันออเดอร์ {order_no} ยอด ฿{total:,.2f} [สถานะ: {initial_status}, กำหนดปลดล็อก: {settle_due_at.strftime('%d/%m/%Y %H:%M')}]")
    return {
        "order_no": order_no,
        "commission_status": initial_status,
        "settle_due_at": settle_due_at.isoformat()
    }

def process_due_commission_settlements():
    """
    ฟังก์ชันเบื้องหลัง (Background/Cron Worker)
    ตรวจสอบและปลดล็อกคอมมิชชันที่ครบกำหนดเวลาอัตโนมัติ (Unsettled -> Settled)
    """
    update_sql = """
        UPDATE order_splits
        SET commission_status = 'settled', settlement_status = 'ready'
        WHERE commission_status = 'unsettled' 
          AND settle_due_at <= NOW();
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(update_sql)
            matured_count = cursor.rowcount
        conn.commit()
    return matured_count
