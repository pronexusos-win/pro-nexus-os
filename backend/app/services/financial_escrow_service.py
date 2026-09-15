from datetime import datetime, timedelta
from backend.app.core.database import get_db_connection

def process_order_financial_escrow(
    order_no: str, 
    total_amount: float, 
    company_slug: str = "tp_extra", 
    branch_id: str = "HEADQUARTER", 
    supplier_code: str = "SUP-BP-001"
):
    """
    แตกเงิน 5 กองตามหลักธรรมาภิบาลการเงินและภาษี:
    - Bucket 1: ซัพพลายเออร์ (65% = ฿650) -> ล็อก 100% ห้ามแตะต้อง
    - Bucket 2: บริหารสาขา (12% = ฿120)
    - Bucket 3: กองทุนน้ำไฟ/ฟิกคอสท์สะสม (3% = ฿30) -> วิ่งเข้า branch_utility_funds
    - Bucket 4: คอมมิชชันตัวแทน/อัปไลน์ (5% = ฿50)
    - Bucket 5: รายได้สุทธิแพลตฟอร์ม (15% = ฿150)
      * แยกคำนวณภาษี VAT 7% = ฿9.81 (รวมใน 150 บาท)
      * หัก ณ ที่จ่าย 3% = ฿4.50
    """
    total = float(total_amount)
    supplier_cost = round(total * 0.65, 2)
    branch_share = round(total * 0.12, 2)
    utility_accrual = round(total * 0.03, 2)
    commission = round(total * 0.05, 2)
    platform_gp = round(total - (supplier_cost + branch_share + utility_accrual + commission), 2)

    # ภาษีบนค่าธรรมเนียมแพลตฟอร์ม
    vat_amount = round(platform_gp * 7 / 107, 2)
    wht_amount = round(platform_gp * 0.03, 2)

    # กำหนดวันจ่ายเงินซัพพลายเออร์ตามรอบ 15 วัน
    payout_due_date = (datetime.now() + timedelta(days=15)).date()

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. บันทึกเงิน 5 กองลง Ledger
            insert_split_sql = """
                INSERT INTO order_financial_splits (
                    order_no, company_slug, branch_id, supplier_code,
                    total_gross_amount, supplier_cost_payable, branch_operating_share,
                    utility_reserve_accrual, marketing_commission, platform_net_gp,
                    platform_vat_amount, withholding_tax_amount,
                    supplier_payout_status, payout_due_date
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'LOCKED_IN_ESCROW', %s)
                ON DUPLICATE KEY UPDATE 
                    total_gross_amount = VALUES(total_gross_amount),
                    supplier_cost_payable = VALUES(supplier_cost_payable),
                    branch_operating_share = VALUES(branch_operating_share),
                    utility_reserve_accrual = VALUES(utility_reserve_accrual),
                    marketing_commission = VALUES(marketing_commission),
                    platform_net_gp = VALUES(platform_net_gp),
                    platform_vat_amount = VALUES(platform_vat_amount),
                    withholding_tax_amount = VALUES(withholding_tax_amount),
                    payout_due_date = VALUES(payout_due_date);
            """
            cursor.execute(insert_split_sql, (
                order_no, company_slug, branch_id, supplier_code,
                total, supplier_cost, branch_share, utility_accrual, commission,
                platform_gp, vat_amount, wht_amount, payout_due_date
            ))

            # 2. หักสะสมเข้ากองทุนค่าน้ำค่าไฟของสาขานั้นอัตโนมัติ
            cursor.execute("""
                UPDATE branch_utility_funds 
                SET current_balance = current_balance + %s,
                    total_accrued = total_accrued + %s
                WHERE branch_id = %s AND company_slug = %s;
            """, (utility_accrual, utility_accrual, branch_id, company_slug))

        conn.commit()

    print(f"🔒 ล็อกเงินซัพพลายเออร์ ฿{supplier_cost:,.2f} และสะสมค่าน้ำไฟ ฿{utility_accrual:,.2f} บิล {order_no} สำเร็จ")
    return {
        "order_no": order_no,
        "supplier_cost_locked": supplier_cost,
        "utility_accrued": utility_accrual,
        "platform_gp": platform_gp,
        "platform_vat": vat_amount,
        "due_date": str(payout_due_date)
    }
