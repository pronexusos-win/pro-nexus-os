import os
import json
import requests
from typing import Dict, Any, Optional

SLIPOK_API_KEY = os.getenv("SLIPOK_API_KEY", "")
SLIPOK_BRANCH_ID = os.getenv("SLIPOK_BRANCH_ID", "")
SLIPOK_ENDPOINT = f"https://api.slipok.com/api/line/apikey/{SLIPOK_BRANCH_ID}"

class SlipOCRService:
    @staticmethod
    def process_slip_image(image_bytes: bytes) -> Dict[str, Any]:
        """
        ส่ง image_bytes ไปตรวจสอบผ่าน SlipOK API
        """
        # กรณีไม่มี API Key ให้ใช้ mock สำหรับ local test
        if not SLIPOK_API_KEY or not SLIPOK_BRANCH_ID:
            print("⚠️ ไม่พบ SLIPOK_API_KEY หรือ SLIPOK_BRANCH_ID ใช้ Mock Data ชั่วคราว")
            return {
                "success": True,
                "trans_amount": 590.00,
                "trans_date": "2026-09-14",
                "trans_time": "19:45:00",
                "sender_bank": "KBANK",
                "receiver_bank": "SCB",
                "receiver_account": "xxx-x-x1234-x",
                "raw_ocr_data": {"mock": True}
            }

        headers = {
            "x-authorization": SLIPOK_API_KEY
        }
        files = {
            "files": ("slip.jpg", image_bytes, "image/jpeg")
        }

        try:
            # ยิงตรวจสอบสลิปแบบ multipart upload
            response = requests.post(SLIPOK_ENDPOINT, headers=headers, files=files, timeout=10)
            res_data = response.json()

            if response.status_code == 200 and res_data.get("success"):
                data = res_data.get("data", {})
                return {
                    "success": True,
                    "trans_amount": float(data.get("amount", 0.0)),
                    "trans_date": data.get("transDate"),
                    "trans_time": data.get("transTime"),
                    "sender_bank": data.get("sendingBank"),
                    "receiver_bank": data.get("receivingBank"),
                    "receiver_account": data.get("receiver", {}).get("account", {}).get("value"),
                    "raw_ocr_data": res_data
                }
            else:
                return {
                    "success": False,
                    "error_message": res_data.get("message", "Slip verification failed"),
                    "raw_ocr_data": res_data
                }
        except Exception as e:
            return {
                "success": False,
                "error_message": f"Connection error: {str(e)}",
                "raw_ocr_data": {}
            }

    @staticmethod
    def match_and_verify_order(line_user_id: str, company_slug: str, ocr_data: Dict[str, Any], conn) -> Dict[str, Any]:
        with conn.cursor() as cursor:
            # 1. เช็กก่อนว่าสลิปนี้ตรวจผ่านหรือไม่
            if not ocr_data.get("success"):
                return {
                    "status": "invalid_slip",
                    "message": ocr_data.get("error_message", "ไม่สามารถอ่านข้อมูลสลิปได้")
                }

            # 2. บันทึกสลิปลงตาราง slips
            insert_slip_sql = """
                INSERT INTO slips (company_slug, line_user_id, image_url, trans_amount, trans_date, trans_time, sender_bank, receiver_bank, receiver_account, raw_ocr_data, verification_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending');
            """
            cursor.execute(insert_slip_sql, (
                company_slug,
                line_user_id,
                "stored_binary_or_cdn",
                ocr_data.get("trans_amount"),
                ocr_data.get("trans_date"),
                ocr_data.get("trans_time"),
                ocr_data.get("sender_bank"),
                ocr_data.get("receiver_bank"),
                ocr_data.get("receiver_account"),
                json.dumps(ocr_data.get("raw_ocr_data", {}))
            ))
            slip_id = cursor.lastrowid

            # 3. หาคำสั่งซื้อ pending_payment ล่าสุด
            find_order_sql = """
                SELECT id, order_no, total_amount 
                FROM orders 
                WHERE line_user_id = %s AND company_slug = %s AND status = 'pending_payment'
                ORDER BY id DESC LIMIT 1;
            """
            cursor.execute(find_order_sql, (line_user_id, company_slug))
            order = cursor.fetchone()

            if not order:
                conn.commit()
                return {"status": "no_pending_order", "slip_id": slip_id}

            required_amount = float(order["total_amount"])
            detected_amount = float(ocr_data.get("trans_amount", 0.0))

            # 4. ตรวจสอบความถูกต้องของยอดเงิน
            if detected_amount >= required_amount:
                # ยอดเงินครบ อัปเดต order และ slip
                cursor.execute("UPDATE orders SET status = 'paid', slip_id = %s WHERE id = %s;", (slip_id, order["id"]))
                cursor.execute("UPDATE slips SET verification_status = 'verified' WHERE id = %s;", (slip_id,))
                conn.commit()

                return {
                    "status": "success",
                    "order_no": order["order_no"],
                    "amount": detected_amount,
                    "slip_id": slip_id
                }
            else:
                conn.commit()
                return {
                    "status": "underpaid",
                    "order_no": order["order_no"],
                    "required": required_amount,
                    "detected": detected_amount,
                    "slip_id": slip_id
                }
