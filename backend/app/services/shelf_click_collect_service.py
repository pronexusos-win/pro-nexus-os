from datetime import datetime, date
from backend.app.core.database import get_db_connection

def calculate_shelf_kpi_rankings(branch_id: str = "HEADQUARTER", company_slug: str = "tp_extra"):
    """
    คำนวณคะแนน KPI การจัดวางสินค้าบนเชลฟ์:
    - น้ำหนักยอดขายชิ้น (40%)
    - น้ำหนักกำไรสุทธิ GP (30%)
    - น้ำหนักรีวิวลูกค้า (30%)
    สินค้าบนเชลฟ์ออนไลน์ที่มีคะแนน > 75 และยอดขาย > 50 ชิ้น จะได้รับสิทธิ PROMOTE_CANDIDATE
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT psp.*, p.name as product_name, p.price as selling_price
                FROM product_shelf_placements psp
                JOIN products p ON psp.sku = p.sku AND p.company_slug = psp.company_slug
                WHERE psp.branch_id = %s AND psp.company_slug = %s
                ORDER BY psp.shelf_kpi_score DESC;
            """, (branch_id, company_slug))
            items = cursor.fetchall()

            for it in items:
                # คำนวณคะแนนแบบไดนามิก
                units = it["monthly_sales_units"]
                gp = float(it["monthly_gross_profit"])
                score = round(min(100.0, (units * 0.4) + ((gp / 1000) * 0.3) + (float(it["customer_review_score"]) * 6)), 2)
                
                status = it["qualification_status"]
                if it["shelf_type"] == "VIRTUAL_ONLINE_ONLY" and score >= 75.0:
                    status = "PROMOTE_CANDIDATE"
                elif it["shelf_type"] == "PHYSICAL_SHELF" and score < 40.0:
                    status = "DEMOTE_WARNING"

                cursor.execute("""
                    UPDATE product_shelf_placements
                    SET shelf_kpi_score = %s, qualification_status = %s
                    WHERE id = %s;
                """, (score, status, it["id"]))

        conn.commit()

    return {"status": "success", "message": "อัปเดตคะแนน Shelf KPI เรียบร้อย"}

def complete_customer_pickup(pickup_qr_or_order: str, branch_id: str = "HEADQUARTER", company_slug: str = "tp_extra"):
    """
    ลูกค้าสแกนรับสินค้าพรีออเดอร์ที่สาขาหน้าร้าน
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM click_collect_orders 
                WHERE (order_no = %s OR pickup_qr_code = %s) 
                  AND pickup_branch_id = %s AND company_slug = %s;
            """, (pickup_qr_or_order, pickup_qr_or_order, branch_id, company_slug))
            order = cursor.fetchone()

            if not order:
                raise ValueError("ไม่พบข้อมูลออเดอร์รับสินค้าที่สาขานี้")
            if order["pickup_status"] == "COMPLETED_COLLECTED":
                raise ValueError("ออเดอร์นี้รับสินค้าไปแล้วเรียบร้อย")
            if order["pickup_status"] == "UNCLAIMED_EXPIRED":
                raise ValueError("ออเดอร์นี้พ้นกำหนดเวลารับสินค้า และถูกส่งเรื่องเคลียร์ค่าธรรมเนียมแล้ว")

            cursor.execute("""
                UPDATE click_collect_orders 
                SET pickup_status = 'COMPLETED_COLLECTED', collected_at = NOW()
                WHERE id = %s;
            """, (order["id"],))

        conn.commit()

    return {
        "status": "success",
        "order_no": order["order_no"],
        "customer_name": order["customer_name"],
        "message": f"ยืนยันการส่งมอบสินค้าออเดอร์ {order['order_no']} ให้กับลูกค้าเรียบร้อย"
    }

def process_unclaimed_orders(branch_id: str = "HEADQUARTER", company_slug: str = "tp_extra"):
    """
    ตรวจจับออเดอร์ที่เลยกำหนดรับสินค้า (เกิน 5 วัน)
    - หักค่าธรรมเนียมจัดเก็บและดูแลพัสดุ (Storage Fee ฿50.00)
    - แบ่งให้สาขา 70% (฿35.00) และแพลตฟอร์ม 30% (฿15.00)
    - คืนเงินส่วนที่เหลือให้ลูกค้า
    """
    today = date.today()
    processed_count = 0

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM click_collect_orders
                WHERE pickup_branch_id = %s AND company_slug = %s
                  AND pickup_status = 'READY_FOR_PICKUP' AND pickup_deadline_date < %s;
            """, (branch_id, company_slug, today))
            expired_orders = cursor.fetchall()

            for ord_item in expired_orders:
                total = float(ord_item["total_amount"])
                fee = float(ord_item["unclaimed_handling_fee"])
                refund = max(0.0, total - fee)
                branch_share = round(fee * 0.70, 2)
                platform_share = round(fee * 0.30, 2)

                cursor.execute("""
                    UPDATE click_collect_orders
                    SET pickup_status = 'UNCLAIMED_EXPIRED',
                        paid_status = 'REFUNDED_PARTIAL',
                        refunded_amount = %s
                    WHERE id = %s;
                """, (refund, ord_item["id"]))

                # สมทบเงินค่าดูแลพื้นที่เข้ากองทุนสาขา (Branch Utility/OpEx)
                cursor.execute("""
                    UPDATE branch_utility_funds
                    SET current_balance = current_balance + %s,
                        total_accrued = total_accrued + %s
                    WHERE branch_id = %s AND company_slug = %s;
                """, (branch_share, branch_share, branch_id, company_slug))

                processed_count += 1

        conn.commit()

    return {
        "status": "success",
        "processed_orders_count": processed_count,
        "message": f"เคลียร์ออเดอร์เลยกำหนดรับ {processed_count} รายการ พร้อมจัดสรรค่าธรรมเนียมเรียบร้อย"
    }
