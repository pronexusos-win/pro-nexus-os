import secrets
from datetime import datetime, date
from backend.app.core.database import get_db_connection

def request_affiliate_payout(creator_code: str, withdraw_amount: float):
    """
    ครีเอเตอร์ยื่นขอถอนเงินค่าโฆษณา/คอมมิชชัน
    หักเงินจากกระเป๋าทันที พร้อมคำนวณภาษี ณ ที่จ่าย 3%
    """
    if withdraw_amount < 300.0:
        raise ValueError("ยอดถอนขั้นต่ำคือ 300.00 บาท")

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. ตรวจสอบยอดคงเหลือของครีเอเตอร์
            cursor.execute("""
                SELECT creator_code, full_name, bank_name, bank_account_no, current_commission_balance
                FROM affiliate_creators WHERE creator_code = %s FOR UPDATE;
            """, (creator_code,))
            creator = cursor.fetchone()

            if not creator:
                raise ValueError(f"ไม่พบข้อมูลผู้แนะนำรหัส {creator_code}")

            balance = float(creator["current_commission_balance"])
            if withdraw_amount > balance:
                raise ValueError(f"ยอดเงินในกระเป๋าไม่เพียงพอ (คงเหลือ ฿{balance:,.2f})")

            # 2. คำนวณภาษีหัก ณ ที่จ่าย 3%
            gross = round(withdraw_amount, 2)
            wht_tax = round(gross * 0.03, 2)
            net_payout = gross - wht_tax

            # 3. รันเลขที่คำขอถอนเงิน และเลขใบ 50 ทวิ
            timestamp_str = datetime.now().strftime("%Y%m%d%H%M")
            random_suffix = secrets.token_hex(2).upper()
            payout_no = f"PAY-{timestamp_str}-{random_suffix}"
            cert_no = f"WHT50-{datetime.now().year}-{random_suffix}"

            # 4. บันทึกประวัติคำขอถอนเงิน
            cursor.execute("""
                INSERT INTO affiliate_payout_requests (
                    payout_no, creator_code, gross_amount, wht_tax_3pct,
                    net_payout_amount, bank_name, bank_account_no,
                    account_holder, status, tax_cert_no
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'APPROVED', %s);
            """, (
                payout_no, creator_code, gross, wht_tax, net_payout,
                creator["bank_name"], creator["bank_account_no"],
                creator["full_name"], cert_no
            ))

            # 5. ออกเอกสารใบ 50 ทวิ
            cursor.execute("""
                INSERT INTO tax_withholding_certificates (
                    cert_no, payout_no, payee_name, payment_amount,
                    tax_rate_pct, tax_deducted, issue_date
                ) VALUES (%s, %s, %s, %s, 3.00, %s, %s);
            """, (cert_no, payout_no, creator["full_name"], gross, wht_tax, date.today()))

            # 6. ตัดยอดเงินคงเหลือในกระเป๋า
            cursor.execute("""
                UPDATE affiliate_creators
                SET current_commission_balance = current_commission_balance - %s,
                    withdrawn_commission = withdrawn_commission + %s
                WHERE creator_code = %s;
            """, (gross, gross, creator_code))

        conn.commit()

    return {
        "status": "success",
        "payout_no": payout_no,
        "tax_cert_no": cert_no,
        "gross_amount": gross,
        "wht_tax": wht_tax,
        "net_transferred": net_payout,
        "bank_account": f"{creator['bank_name']} ({creator['bank_account_no']})"
    }
