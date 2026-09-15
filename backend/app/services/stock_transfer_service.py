from datetime import datetime
from backend.app.core.database import get_db_connection

def create_stock_transfer_manifest(
    origin_branch: str, destination_branch: str,
    sku: str, lot_no: str, quantity: int,
    sender_emp: str, unit_weight: float = 150.0,
    company_slug: str = "tp_extra"
):
    """
    สร้างใบโอนย้ายสต็อก ตัดจำนวนจากต้นทาง และคำนวณน้ำหนักมาตรฐานรวมกล่อง (+200g)
    """
    expected_weight = (quantity * unit_weight) + 200.0  # น้ำหนักสินค้า + กล่องบรรจุภัณฑ์
    transfer_no = f"TRF-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # ตรวจสอบสต็อกต้นทาง
            cursor.execute("""
                SELECT remaining_quantity FROM product_lots
                WHERE sku = %s AND lot_no = %s AND branch_id = %s AND company_slug = %s;
            """, (sku, lot_no, origin_branch, company_slug))
            lot = cursor.fetchone()

            if not lot or lot["remaining_quantity"] < quantity:
                raise ValueError("สต็อกในล็อตต้นทางไม่เพียงพอสำหรับการโอนย้าย")

            # 1. บันทึกหัวใบโอนย้าย
            cursor.execute("""
                INSERT INTO stock_transfers (
                    transfer_no, company_slug, origin_branch_id, destination_branch_id,
                    expected_weight_grams, sender_emp_code, transfer_status, dispatched_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'IN_TRANSIT', NOW());
            """, (transfer_no, company_slug, origin_branch, destination_branch, expected_weight, sender_emp))

            # 2. บันทึกรายการสินค้า
            cursor.execute("""
                INSERT INTO stock_transfer_items (transfer_no, sku, lot_no, quantity, unit_weight_grams)
                VALUES (%s, %s, %s, %s, %s);
            """, (transfer_no, sku, lot_no, quantity, unit_weight))

            # 3. ตัดสต็อกต้นทาง
            cursor.execute("""
                UPDATE product_lots
                SET remaining_quantity = remaining_quantity - %s
                WHERE sku = %s AND lot_no = %s AND branch_id = %s AND company_slug = %s;
            """, (quantity, sku, lot_no, origin_branch, company_slug))

        conn.commit()

    return {
        "status": "success",
        "transfer_no": transfer_no,
        "expected_weight_grams": expected_weight,
        "message": f"ออกใบส่งมอบ {transfer_no} และส่งพัสดุเข้าสถานะ IN_TRANSIT เรียบร้อย"
    }

def verify_and_receive_transfer(
    transfer_no: str, actual_weight_grams: float,
    receiver_emp: str, company_slug: str = "tp_extra"
):
    """
    สาขาปลายทางตรวจชั่งน้ำหนักพัสดุก่อนรับเข้าสต็อก (±3% Gate)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM stock_transfers 
                WHERE transfer_no = %s AND company_slug = %s;
            """, (transfer_no, company_slug))
            trf = cursor.fetchone()

            if not trf:
                raise ValueError("ไม่พบใบโอนย้ายสินค้า")
            if trf["transfer_status"] == "RECEIVED_VERIFIED":
                raise ValueError("ใบโอนย้ายนี้ได้รับการตรวจรับเข้าสต็อกไปแล้ว")

            expected = float(trf["expected_weight_grams"])
            diff_grams = abs(actual_weight_grams - expected)
            discrepancy_pct = round((diff_grams / expected) * 100, 2) if expected > 0 else 0

            # หากน้ำหนักคลาดเคลื่อนเกิน ±3%
            is_discrepancy = discrepancy_pct > 3.0
            new_status = "DISCREPANCY_FLAGGED" if is_discrepancy else "RECEIVED_VERIFIED"

            cursor.execute("""
                UPDATE stock_transfers
                SET actual_received_weight_grams = %s,
                    weight_discrepancy_pct = %s,
                    receiver_emp_code = %s,
                    transfer_status = %s,
                    received_at = NOW()
                WHERE id = %s;
            """, (actual_weight_grams, discrepancy_pct, receiver_emp, new_status, trf["id"]))

            # หากผ่านเกณฑ์ ให้นำสต็อกเข้าสาขาปลายทาง
            if not is_discrepancy:
                cursor.execute("""
                    SELECT sku, lot_no, quantity FROM stock_transfer_items WHERE transfer_no = %s;
                """, (transfer_no,))
                items = cursor.fetchall()

                for it in items:
                    cursor.execute("""
                        INSERT INTO product_lots (
                            lot_no, sku, company_slug, branch_id, ownership_type, supplier_code,
                            mfg_date, expiry_date, received_date, total_shelf_life_days, remaining_shelf_life_pct,
                            received_quantity, remaining_quantity, unit_cost, selling_price, lot_status
                        )
                        SELECT lot_no, sku, company_slug, %s, ownership_type, supplier_code,
                               mfg_date, expiry_date, CURDATE(), total_shelf_life_days, remaining_shelf_life_pct,
                               %s, %s, unit_cost, selling_price, 'NORMAL'
                        FROM product_lots
                        WHERE sku = %s AND lot_no = %s AND branch_id = %s LIMIT 1
                        ON DUPLICATE KEY UPDATE remaining_quantity = remaining_quantity + VALUES(remaining_quantity);
                    """, (trf["destination_branch_id"], it["quantity"], it["quantity"], it["sku"], it["lot_no"], trf["origin_branch_id"]))

        conn.commit()

    return {
        "status": "success",
        "transfer_no": transfer_no,
        "expected_weight": expected,
        "actual_weight": actual_weight_grams,
        "discrepancy_pct": discrepancy_pct,
        "is_discrepancy": is_discrepancy,
        "new_status": new_status,
        "message": "น้ำหนักถูกต้อง นำเข้าสต็อกสาขาสำเร็จ" if not is_discrepancy else f"🚨 เตือนภัย! น้ำหนักคลาดเคลื่อน {discrepancy_pct}% ล็อกการรับเข้าเพื่อสอบสวน"
    }
