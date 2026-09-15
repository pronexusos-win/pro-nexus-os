from datetime import datetime, date
from backend.app.core.database import get_db_connection

def get_blind_count_sheet(branch_id: str = "HEADQUARTER", company_slug: str = "tp_extra"):
    """
    ดึงรายการสินค้าและล็อตสำหรับส่งให้พนักงานตรวจนับ (ปิดซ่อนจำนวนคงเหลือในระบบ)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT pl.id as lot_id, pl.sku, p.name as product_name, pl.lot_no,
                       DATE_FORMAT(pl.expiry_date, '%d/%m/%Y') as expiry_date
                FROM product_lots pl
                JOIN products p ON pl.sku = p.sku AND p.company_slug = pl.company_slug
                WHERE pl.branch_id = %s AND pl.company_slug = %s AND pl.remaining_quantity > 0
                ORDER BY pl.sku ASC;
            """, (branch_id, company_slug))
            items = cursor.fetchall()

    return {
        "status": "success",
        "branch_id": branch_id,
        "audit_date": str(date.today()),
        "total_lots_to_count": len(items),
        "items": items
    }

def process_blind_count_submission(
    counted_records: list, counter_emp: str, witness_emp: str,
    branch_id: str = "HEADQUARTER", company_slug: str = "tp_extra"
):
    """
    ประมวลผลการส่งยอดตรวจนับตาบอด เปรียบเทียบกับระบบ และคำนวณ Accuracy Rate
    """
    today = date.today()
    audit_no = f"AUD-{datetime.now().strftime('%Y%m%d%H%M')}"
    
    total_items = len(counted_records)
    matched_count = 0
    discrepant_count = 0
    net_variance_val = 0.0

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # สร้าง Header รอบการตรวจนับ
            cursor.execute("""
                INSERT INTO inventory_cycle_audits (
                    audit_no, company_slug, branch_id, audit_date, counter_emp_code, witness_emp_code
                )
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (audit_no, company_slug, branch_id, today, counter_emp, witness_emp))

            for r in counted_records:
                sku = r["sku"]
                lot_no = r["lot_no"]
                user_counted_qty = int(r["counted_qty"])

                # ดึงยอดจริงในระบบ
                cursor.execute("""
                    SELECT remaining_quantity, unit_cost FROM product_lots
                    WHERE sku = %s AND lot_no = %s AND branch_id = %s AND company_slug = %s;
                """, (sku, lot_no, branch_id, company_slug))
                lot_row = cursor.fetchone()

                system_qty = lot_row["remaining_quantity"] if lot_row else 0
                unit_cost = float(lot_row["unit_cost"]) if lot_row else 0.0

                diff_qty = user_counted_qty - system_qty
                var_value = diff_qty * unit_cost
                net_variance_val += var_value

                if diff_qty == 0:
                    matched_count += 1
                    status = "MATCH"
                else:
                    discrepant_count += 1
                    status = "SHORTAGE" if diff_qty < 0 else "OVERAGE"

                # บันทึกรายละเอียดรายชิ้น
                cursor.execute("""
                    INSERT INTO cycle_audit_items (
                        audit_no, sku, lot_no, system_expected_qty, counted_qty,
                        variance_qty, unit_cost, variance_value, item_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (audit_no, sku, lot_no, system_qty, user_counted_qty, diff_qty, unit_cost, var_value, status))

            accuracy_pct = round((matched_count / total_items) * 100, 2) if total_items > 0 else 100.0
            final_status = "RECONCILED_PERFECT" if discrepant_count == 0 else "DISCREPANCY_ADJUSTED"

            cursor.execute("""
                UPDATE inventory_cycle_audits
                SET total_items_audited = %s,
                    matched_items_count = %s,
                    discrepant_items_count = %s,
                    net_variance_value = %s,
                    accuracy_rate_pct = %s,
                    audit_status = %s,
                    manager_signed_at = NOW()
                WHERE audit_no = %s;
            """, (total_items, matched_count, discrepant_count, net_variance_val, accuracy_pct, final_status, audit_no))

        conn.commit()

    return {
        "status": "success",
        "audit_no": audit_no,
        "accuracy_rate_pct": accuracy_pct,
        "matched_count": matched_count,
        "discrepant_count": discrepant_count,
        "net_variance_value": net_variance_val,
        "is_perfect": discrepant_count == 0,
        "message": f"ตรวจนับรอบ {audit_no} สำเร็จ (ความแม่นยำ: {accuracy_pct}%)"
    }
