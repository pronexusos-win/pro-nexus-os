import os
import sys
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    RichMenuRequest,
    RichMenuSize,
    RichMenuArea,
    RichMenuBounds,
    URIAction,
    MessageAction
)

# ดึง Token จาก Environment Variables (หรือระบุตรงๆ สำหรับทดสอบ)
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN_TP_EXTRA")
LIFF_ID = os.getenv("LINE_LIFF_ID_TP_EXTRA", "YOUR_LIFF_ID")

if not CHANNEL_ACCESS_TOKEN:
    print("❌ ไม่พบค่า LINE_CHANNEL_ACCESS_TOKEN_TP_EXTRA ใน Environment Variables")
    sys.exit(1)

LIFF_URL_SHOP = f"https://liff.line.me/{LIFF_ID}"
LIFF_URL_HISTORY = f"https://liff.line.me/{LIFF_ID}/history.html"

def generate_sample_rich_menu_image() -> bytes:
    """สร้างภาพ Rich Menu ขนาดมาตรฐาน 2500 x 843 px แบบ 3 ปุ่ม"""
    width, height = 2500, 843
    img = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # แบ่ง 3 โซนแนวตั้ง (กว้างโซนละ 833.33 px)
    cols = [
        {"bg": "#06C755", "label": "🛒 ช้อปปิ้งแบ่งปัน", "sub": "สั่งซื้อสินค้าโปรโมชัน"},
        {"bg": "#1E293B", "label": "📋 ประวัติสั่งซื้อ", "sub": "ตรวจเช็กสถานะออเดอร์"},
        {"bg": "#F59E0B", "label": "🧾 แจ้งชำระเงิน", "sub": "ส่งสลิปเพื่อตรวจสอบ"}
    ]

    col_width = width // 3
    for i, col in enumerate(cols):
        x0 = i * col_width
        x1 = (i + 1) * col_width if i < 2 else width
        draw.rectangle([x0, 0, x1, height], fill=col["bg"])
        # เส้นคั่นระหว่างปุ่ม
        draw.line([x0, 0, x0, height], fill="#FFFFFF", width=4)

    # ส่งออกเป็นไบนารี JPEG
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()

def create_and_set_rich_menu():
    conf = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

    with ApiClient(conf) as api_client:
        messaging_api = MessagingApi(api_client)
        blob_api = MessagingApiBlob(api_client)

        print("🚀 กำลังสร้างโครงสร้าง Rich Menu...")

        # 1. กำหนดขนาดและพิกัด Bounds (2500 x 843 px)
        rich_menu_request = RichMenuRequest(
            size=RichMenuSize(width=2500, height=843),
            selected=True,
            name="BAENGPUN_MAIN_MENU",
            chat_bar_text="แตะเพื่อเปิดเมนู",
            areas=[
                # ปุ่มที่ 1: เปิดหน้าร้าน LIFF Shop (ซ้าย)
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=URIAction(label="Open Shop", uri=LIFF_URL_SHOP)
                ),
                # ปุ่มที่ 2: เปิดหน้าประวัติสั่งซื้อ LIFF History (กลาง)
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=0, width=834, height=843),
                    action=URIAction(label="Order History", uri=LIFF_URL_HISTORY)
                ),
                # ปุ่มที่ 3: ส่งข้อความเปิดห้องแช็ตส่งสลิป (ขวา)
                RichMenuArea(
                    bounds=RichMenuBounds(x=1667, y=0, width=833, height=843),
                    action=MessageAction(label="Send Slip", text="ส่งสลิปโอนเงิน")
                )
            ]
        )

        # 2. ยิงสร้าง Rich Menu ไปยัง LINE
        menu_response = messaging_api.create_rich_menu(rich_menu_request=rich_menu_request)
        rich_menu_id = menu_response.rich_menu_id
        print(f"✅ สร้าง Rich Menu สำเร็จ! ID: {rich_menu_id}")

        # 3. อัปโหลดรูปภาพ Rich Menu
        print("🖼️ กำลังอัปโหลดภาพพื้นหลัง Rich Menu...")
        image_bytes = generate_sample_rich_menu_image()
        blob_api.set_rich_menu_image(
            rich_menu_id=rich_menu_id,
            body=image_bytes,
            _headers={"Content-Type": "image/jpeg"}
        )
        print("✅ อัปโหลดภาพเสร็จสิ้น!")

        # 4. ตั้งเป็น Default Rich Menu สำหรับทุกคนที่แอดไลน์เข้ามา
        print("🔗 กำลังตั้งค่าเป็น Default Menu...")
        messaging_api.set_default_rich_menu(rich_menu_id=rich_menu_id)
        print(f"🎉 ตั้งค่าสำเร็จ! ผู้ใช้ทุกคนจะเห็น Rich Menu นี้ทันทีเมื่อเปิดแช็ต")

if __name__ == "__main__":
    create_and_set_rich_menu()
