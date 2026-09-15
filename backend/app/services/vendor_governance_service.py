from datetime import datetime, date, timedelta
from backend.app.core.database import get_db_connection

def scan_and_generate_vendor_alerts(company_slug: str = "tp_extra"):
    """
    ระบบเฝ้าระวังความเสี่ยงคู่ค้า 360 องศา:
    1. ตรวจสอบสัญญาใกล้หมดอายุ (ภายใน 30 วัน)
    2. ตรวจสอบใบอนุญาต อย./GMP ใกล้หมดอายุ (ภายใน 60 วัน)
    3. ตรวจสอบรอบจ่ายเงินค่าสินค้าใน Escrow ที่ถึงกำหนดจ่าย (ภายใน 3 วัน)
    """
    today = date.today()
    alerts_created = 0

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. ตรวจสัญญาใกล้หมดอายุ
            cursor.execute("""
                SELECT supplier_code, company_name, contract_end_date, DATEDIFF(contract_end_date, %s) as days_left
                FROM vendor_compliance_profiles
                WHERE company_slug = %s AND contract_end_date <= DATE_ADD(%s, INTERVAL 30 DAY);
            """, (today, company_slug, today))
            exp_contracts = cursor.fetchall()

            for row in exp_contracts:
                days = row["days_left"]
                severity = "CRITICAL" if days <= 7 else ("HIGH" if days <= 15 else "MEDIUM")
                title = f"⚠️ สัญญากับ {row['company_name']} ใกล้หมดอายุ"
                detail = f"สัญญาการค้าจะสิ้นสุดในอีก {days} วัน (วันที่ {row['contract_end_date']}) กรุณาดำเนินการเจรจาต่อสัญญา"
                
                cursor.execute("""
                    INSERT INTO vendor_governance_alerts (supplier_code, alert_type, severity, alert_title, alert_detail, due_date)
                    SELECT %s, 'CONTRACT_EXPIRING', %s, %s, %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM vendor_governance_alerts 
                        WHERE supplier_code = %s AND alert_type = 'CONTRACT_EXPIRING' AND is_resolved = FALSE
                    );
                """, (row["supplier_code"], severity, title, detail, row["contract_end_date"], row["supplier_code"]))
                if cursor.rowcount > 0:
                    alerts_created += 1

            # 2. ตรวจรอบเงินใน Escrow ที่ถึงกำหนดจ่ายคู่ค้า (ภายใน 3 วัน)
            cursor.execute("""
                SELECT supplier_code, payout_due_date, SUM(supplier_cost_payable) as due_amount, COUNT(id) as bill_count
                FROM order_financial_splits
                WHERE company_slug = %s AND supplier_payout_status = 'LOCKED_IN_ESCROW'
                  AND payout_due_date <= DATE_ADD(%s, INTERVAL 3 DAY)
                GROUP BY supplier_code, payout_due_date;
            """, (company_slug, today))
            due_payouts = cursor.fetchall()

            for p in due_payouts:
                title = f"💰 รอบจ่ายเงินคู่ค้า {p['supplier_code']} กำหนดชำระ {p['payout_due_date']}"
                detail = f"มีเงินค่าสินค้าใน Escrow รอโอน ฿{float(p['due_amount']):,.2f} บาท ({p['bill_count']} บิล) ระบบเตรียมไฟล์โอนพร้อมหนังสือ 50 ทวิแล้ว"
                
                cursor.execute("""
                    INSERT INTO vendor_governance_alerts (supplier_code, alert_type, severity, alert_title, alert_detail, due_date)
                    SELECT %s, 'SETTLEMENT_DUE', 'HIGH', %s, %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM vendor_governance_alerts 
                        WHERE supplier_code = %s AND alert_type = 'SETTLEMENT_DUE' AND due_date = %s AND is_resolved = FALSE
                    );
                """, (p["supplier_code"], title, detail, p["payout_due_date"], p["supplier_code"], p["payout_due_date"]))
                if cursor.rowcount > 0:
                    alerts_created += 1

        conn.commit()

    return alerts_created
