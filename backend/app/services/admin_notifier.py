import os
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage

COMPANY_TOKENS = {
    "tp_extra": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_TP_EXTRA"),
    "pro_nexus": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_PRO_NEXUS"),
    "luck_kio": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_LUCK_KIO"),
    "peak_icon": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_PEAK_ICON")
}

COMPANY_ADMIN_GROUPS = {
    "tp_extra": os.getenv("ADMIN_LINE_GROUP_ID_TP_EXTRA"),
    "pro_nexus": os.getenv("ADMIN_LINE_GROUP_ID_PRO_NEXUS"),
    "luck_kio": os.getenv("ADMIN_LINE_GROUP_ID_LUCK_KIO"),
    "peak_icon": os.getenv("ADMIN_LINE_GROUP_ID_PEAK_ICON")
}

def notify_admin_order_paid(order_data: dict):
    """ยิงข้อความแจ้งเตือนสรุปออเดอร์พร้อมที่อยู่จัดส่งเข้ากลุ่ม LINE แอดมิน/ทีมงาน"""
    company = order_data.get("company_slug", "tp_extra")
    token = COMPANY_TOKENS.get(company)
    group_id = COMPANY_ADMIN_GROUPS.get(company)

    if not token or not group_id:
        print(f"⚠️ ข้ามการส่งข้อความเข้ากลุ่ม (Token หรือ Group ID ของ {company} ยังไม่ได้ตั้งค่า)")
        return

    order_no = order_data.get("order_no", "-")
    total_amount = order_data.get("total_amount", 0.0)
    customer_name = order_data.get("customer_name") or "ไม่ได้ระบุชื่อ"
    customer_phone = order_data.get("customer_phone") or "ไม่ได้ระบุเบอร์"
    shipping_address = order_data.get("shipping_address") or "ไม่ได้ระบุที่อยู่"
    slip_time = order_data.get("slip_time", "ล่าสุด")

    message_text = (
        f"🔔 มีออเดอร์ชำระเงินใหม่! [{company.upper()}]\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔖 รหัสคำสั่งซื้อ: {order_no}\n"
        f"💰 ยอดเงินที่โอน: ฿{float(total_amount):,.2f}\n"
        f"⏰ เวลาชำระ: {slip_time}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 ผู้รับ: {customer_name}\n"
        f"📞 เบอร์โทร: {customer_phone}\n"
        f"📍 ที่อยู่จัดส่ง:\n{shipping_address}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 ทีมแพ็กสินค้าสามารถเตรียมจัดส่งได้เลยครับ"
    )

    try:
        conf = Configuration(access_token=token)
        with ApiClient(conf) as api_client:
            line_api = MessagingApi(api_client)
            line_api.push_message(
                PushMessageRequest(
                    to=group_id,
                    messages=[TextMessage(text=message_text)]
                )
            )
        print(f"✅ ส่งแจ้งเตือนออเดอร์ {order_no} เข้ากลุ่ม LINE แอดมินสำเร็จ!")
    except Exception as e:
        print(f"⚠️ เกิดข้อผิดพลาดในการส่งแจ้งเตือนเข้ากลุ่มแอดมิน: {e}")
