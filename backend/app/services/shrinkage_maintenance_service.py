from datetime import datetime
from backend.app.core.database import get_db_connection

def record_inventory_writeoff(
    sku: str, quantity: int, reason_type: str,
    witness_emp: str, manager_emp: str,
    evidence_url: str = None, police_report: str = None,
    branch_id: str = "HEADQUARTER", company_slug: str = "tp_extra"
):
    """
    บันทึกตัดจ่ายสินค้าสูญหาย/ชำรุด พร้อมตัดจำนวนสต็อกจริงออกจากคลัง
    - EXPIRED / DAMAGED: ลงรายจ่ายทางภาษีได้ (TAX_DEDUCTIBLE_NO_VAT ตาม ป.79/2541)
    - LOST_STOLEN (ไม่มีแจ้งความ): สรรพากรมองเป็นการขาย ต้องคำนวณ VAT 7% (DEEMED_SALE_WITH_VAT)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # ดึงราคาต้นทุนสินค้า
            cursor.execute("SELECT name, cost_price, stock_quantity FROM products WHERE sku = %s AND company_slug = %s;", (sku, company_slug))
            prod = cursor.fetchone()
            if not prod:
                raise ValueError(f"ไม่พบ SKU: {sku}")

            cost_price = float(prod.get("cost_price") or 0.0)
            total_loss = cost_price * quantity

            # กำหนดการจัดการทางภาษี
            if reason_type == "LOST_STOLEN" and not police_report:
                tax_treatment = "DEEMED_SALE_WITH_VAT"
            else:
                tax_treatment = "TAX_DEDUCTIBLE_NO_VAT"

            wof_no = f"WOF-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # 1. บันทึกลงตาราง Write-Off
            cursor.execute("""
                INSERT INTO inventory_writeoffs (
                    writeoff_no, company_slug, branch_id, sku, product_name, quantity,
                    unit_cost, total_loss_value, reason_type, tax_treatment,
                    evidence_photo_url, police_report_no, witness_emp_code, manager_authorizer
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                wof_no, company_slug, branch_id, sku, prod["name"], quantity,
                cost_price, total_loss, reason_type, tax_treatment,
                evidence_url, police_report, witness_emp, manager_emp
            ))

            # 2. ตัดสต็อกออกจากระบบจริงทันที
            cursor.execute("""
                UPDATE products 
                SET stock_quantity = GREATEST(0, stock_quantity - %s)
                WHERE sku = %s AND company_slug = %s;
            """, (quantity, sku, company_slug))

        conn.commit()

    return {
        "status": "success",
        "writeoff_no": wof_no,
        "product_name": prod["name"],
        "quantity_written_off": quantity,
        "total_loss": total_loss,
        "tax_treatment": tax_treatment
    }

def record_asset_maintenance(
    asset_name: str, cost_amount: float, vendor_name: str, vendor_tax_id: str,
    invoice_no: str, authorized_by: str, paid_from_fund: str = "BRANCH_UTILITY_RESERVE",
    branch_id: str = "HEADQUARTER", company_slug: str = "tp_extra"
):
    """
    บันทึกค่าซ่อมบำรุงและตัดจ่ายจากกองทุนสำรองสาธารณูปโภค (Utility Reserve)
    พร้อมคำนวณหักภาษี ณ ที่จ่าย 3% (ภ.ง.ด. 53/3)
    """
    wht_3pct = round(cost_amount * 0.03, 2)
    mnt_no = f"MNT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. บันทึกประวัติการซ่อมบำรุง
            cursor.execute("""
                INSERT INTO asset_maintenance_logs (
                    maint_no, company_slug, branch_id, asset_name, expense_category,
                    vendor_tax_id, vendor_name, invoice_no, cost_amount,
                    wht_deducted_3pct, paid_from_fund, authorized_by
                )
                VALUES (%s, %s, %s, %s, 'ROUTINE_REPAIR', %s, %s, %s, %s, %s, %s, %s);
            """, (
                mnt_no, company_slug, branch_id, asset_name,
                vendor_tax_id, vendor_name, invoice_no, cost_amount,
                wht_3pct, paid_from_fund, authorized_by
            ))

            # 2. หากตัดจากกองทุนน้ำไฟสำรอง ให้หักยอดออกจาก current_balance
            if paid_from_fund == "BRANCH_UTILITY_RESERVE":
                cursor.execute("""
                    UPDATE branch_utility_funds
                    SET current_balance = current_balance - %s,
                        total_paid_out = total_paid_out + %s
                    WHERE branch_id = %s AND company_slug = %s;
                """, (cost_amount, cost_amount, branch_id, company_slug))

        conn.commit()

    return {
        "status": "success",
        "maint_no": mnt_no,
        "net_paid": cost_amount - wht_3pct,
        "wht_3pct": wht_3pct,
        "paid_from": paid_from_fund
    }
