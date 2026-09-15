import secrets
from datetime import datetime, date
from backend.app.core.database import get_db_connection

def book_branch_cash_pickup(creator_code: str, amount: float, branch_code: str, appointment_date: str, time_slot: str):
    """
    จองคิวนัดรับเงินสดที่สาขา:
    - ตัดยอดเงินในกระเป๋าคอมมิชชัน
    - หักภาษี 3% ตามเกณฑ์ สรรพากร
    - แจก Bonus Points 50 แต้ม
    - ออกรหัส OTP และ QR ปลอดภัย
    """
    if amount < 300.0:
        raise ValueError("ยอดถอนขั้นต่ำคือ 300.00 บาท")

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. เช็กยอดเงินครีเอเตอร์
            cursor.execute("""
                SELECT creator_code, full_name, current_commission_balance, reward_points
                FROM affiliate_creators WHERE creator_code = %s FOR UPDATE;
            """, (creator_code,))
            creator = cursor.fetchone()

            if not creator:
                raise ValueError("ไม่พบข้อมูลผู้ใช้")

            balance = float(creator["current_commission_balance"])
            if amount > balance:
                raise ValueError(f"ยอดเงินในกระเป๋าไม่พอ (คงเหลือ ฿{balance:,.2f})")

            # 2. คำนวณภาษีหัก ณ ที่จ่าย 3%
            gross = round(amount, 2)
            wht_tax = round(gross * 0.03, 2)
            net_cash = gross - wht_tax

            # 3. รหัสตรวจสอบ OTP และ QR
            timestamp_str = datetime.now().strftime("%y%m%d%H%M")
            rand_suffix = secrets.token_hex(2).upper()
            pickup_code = f"CPK-{timestamp_str}-{rand_suffix}"
            secure_otp = f"{secrets.randbelow(9000) + 1000}"  # OTP 4 หลัก
            qr_token = f"CASH-PICKUP:{pickup_code}:{secure_otp}"
            cert_no = f"WHT50-{datetime.now().year}-{rand_suffix}"

            # 4. บันทึกคำขอนัดรับเงิน
            cursor.execute("""
                INSERT INTO branch_cash_pickups (
                    pickup_code, creator_code, gross_amount, wht_tax_3pct,
                    net_cash_amount, branch_code, appointment_date, time_slot,
                    bonus_points_earned, secure_otp, pickup_qr_token, tax_cert_no
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 50, %s, %s, %s);
            """, (
                pickup_code, creator_code, gross, wht_tax,
                net_cash, branch_code, appointment_date, time_slot,
                secure_otp, qr_token, cert_no
            ))

            # 5. ตัดกระเป๋าคอมมิชชัน และบวกแต้มพิเศษ 50 แต้มให้ทันที
            cursor.execute("""
                UPDATE affiliate_creators
                SET current_commission_balance = current_commission_balance - %s,
                    reward_points = reward_points + 50
                WHERE creator_code = %s;
            """, (gross, creator_code))

        conn.commit()

    return {
        "status": "success",
        "pickup_code": pickup_code,
        "net_cash_amount": net_cash,
        "secure_otp": secure_otp,
        "qr_token": qr_token,
        "branch_code": branch_code,
        "appointment_date": appointment_date,
        "time_slot": time_slot,
        "bonus_points": 50
    }

def confirm_cash_payout_at_branch(pickup_code: str, otp_entered: str, cashier_id: str):
    """
    แคชเชียร์หน้าร้านสแกน QR หรือกดใส่รหัส OTP เพื่อจ่ายเงินสด
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM branch_cash_pickups 
                WHERE pickup_code = %s AND status = 'PENDING_VISIT' FOR UPDATE;
            """, (pickup_code,))
            record = cursor.fetchone()

            if not record:
                raise ValueError("ไม่พบรายการนัดหมาย หรือรายการนี้ถูกดำเนินการไปแล้ว")

            if record["secure_otp"] != otp_entered.strip():
                raise ValueError("รหัส OTP ไม่ถูกต้อง! ปฏิเสธการจ่ายเงินสดเพื่อความปลอดภัย")

            # อัปเดตสถานะว่าจ่ายเงินสดเรียบร้อย
            cursor.execute("""
                UPDATE branch_cash_pickups
                SET status = 'COMPLETED',
                    processed_by_cashier = %s,
                    collected_at = NOW()
                WHERE pickup_code = %s;
            """, (cashier_id, pickup_code))

        conn.commit()

    return {
        "status": "success",
        "message": f"ยืนยันการจ่ายเงินสดจำนวน ฿{float(record['net_cash_amount']):,.2f} เรียบร้อยแล้ว",
        "net_cash_paid": float(record["net_cash_amount"]),
        "creator_code": record["creator_code"],
        "tax_cert_no": record["tax_cert_no"]
    }

def process_no_show_penalties():
    """
    ระบบรันอัตโนมัติสิ้นวัน: รายการที่เลยวันนัดแล้วไม่มา จะถูกปรับลดแต้ม 30 แต้ม
    """
    today_str = date.today().strftime("%Y-%m-%d")
    penalized_count = 0

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, pickup_code, creator_code, penalty_points
                FROM branch_cash_pickups
                WHERE status = 'PENDING_VISIT' AND appointment_date < %s;
            """, (today_str,))
            expired_list = cursor.fetchall()

            for item in expired_list:
                # ปรับสถานะเป็น NO_SHOW_PENALIZED
                cursor.execute("""
                    UPDATE branch_cash_pickups SET status = 'NO_SHOW_PENALIZED' WHERE id = %s;
                """, (item["id"],))

                # หักแต้มความประพฤติ/ค่าสำรองสภาพคล่อง 30 แต้ม
                cursor.execute("""
                    UPDATE affiliate_creators
                    SET reward_points = GREATEST(0, reward_points - %s)
                    WHERE creator_code = %s;
                """, (item["penalty_points"], item["creator_code"]))
                penalized_count += 1

        conn.commit()

    return {"status": "success", "penalized_count": penalized_count}
