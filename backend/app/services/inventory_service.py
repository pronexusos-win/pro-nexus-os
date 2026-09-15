import os
from backend.app.core.database import get_db_connection
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

def deduct_stock_for_order(order_no: str, company_slug: str = "tp_extra"):
    """
    ตัดสต็อกสินค้าในออเดอร์ และแจ้งเตือน LINE หากสต็อกคงเหลือ <= เกณฑ์เตือน
    """
    low_stock_alerts = []

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. ค้นหารายการสินค้าในออเดอร์
            cursor.execute(
                "SELECT sku, product_name, quantity FROM order_items WHERE order_no = %s;",
                (order_no,)
            )
            items = cursor.fetchall()

            # หากออเดอร์ยังไม่มีรายการใน order_items (เช่น ออเดอร์ทดสอบเดิม) ให้ตัด SKU พื้นฐาน
            if not items:
                cursor.execute(
                    "SELECT sku, name FROM products WHERE company_slug = %s LIMIT 1;",
                    (company_slug,)
                )
                default_prod = cursor.fetchone()
                if default_prod:
                    items = [{"sku": default_prod["sku"], "product_name": default_prod["name"], "quantity": 1}]

            # 2. ตัดสต็อกทีละรายการ
            for item in items:
                sku = item["sku"]
                qty = item["quantity"]

                # อัปเดตลดสต็อก
                cursor.execute(
                    """
                    UPDATE products 
                    SET stock_quantity = GREATEST(0, stock_quantity - %s) 
                    WHERE sku = %s AND company_slug = %s;
                    """,
                    (qty, sku, company_slug)
                )

                # ดึงยอดคงเหลือมาตรวจสอบ
                cursor.execute(
                    """
                    SELECT sku, name, stock_quantity, low_stock_threshold 
                    FROM products 
                    WHERE sku = %s AND company_slug = %s;
                    """,
                    (sku, company_slug)
                )
                prod = cursor.fetchone()
                if prod and prod["stock_quantity"] <= prod["low_stock_threshold"]:
                    low_stock_alerts.append(prod)

        conn.commit()

    # 3. ยิง LINE แจ้งเตือนแอดมินหากมีสินค้าใกล้หมด
    if low_stock_alerts:
        send_low_stock_notification(company_slug, low_stock_alerts)

def send_low_stock_notification(company_slug: str, products: list):
    token = COMPANY_TOKENS.get(company_slug) or os.getenv("LINE_CHANNEL_ACCESS_TOKEN_TP_EXTRA")
    group_id = COMPANY_ADMIN_GROUPS.get(company_slug) or os.getenv("ADMIN_LINE_GROUP_ID_TP_EXTRA")

    if not token or not group_id:
        print(f"⚠️ ข้ามแจ้งเตือนสต็อกใกล้หมด (ไม่มี Token หรือ Group ID ของ {company_slug})")
        return

    prod_lines = "\n".join([
        f"• [{p['sku']}] {p['name']}\n  คงเหลือ: {p['stock_quantity']} ชิ้น (เกณฑ์เตือน: {p['low_stock_threshold']} ชิ้น)"
        for p in products
    ])

    alert_text = (
        f"⚠️ แจ้งเตือนสินค้าใกล้หมดสต็อก! [{company_slug.upper()}]\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{prod_lines}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"กรุณาตรวจสอบและเตรียมเติมสต็อกสินค้าครับ 🏭"
    )

    try:
        conf = Configuration(access_token=token)
        with ApiClient(conf) as api_client:
            line_api = MessagingApi(api_client)
            line_api.push_message(
                PushMessageRequest(
                    to=group_id,
                    messages=[TextMessage(text=alert_text)]
                )
            )
        print(f"✅ ส่งแจ้งเตือนสินค้าใกล้หมดเข้ากลุ่ม LINE สำเร็จ ({len(products)} รายการ)")
    except Exception as e:
        print(f"⚠️ เกิดข้อผิดพลาดในการส่งแจ้งเตือนสต็อก: {e}")
