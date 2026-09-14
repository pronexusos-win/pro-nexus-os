import os
from fastapi import APIRouter, HTTPException, Query, Header, status
from pydantic import BaseModel, Field
from typing import Optional
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from backend.app.core.database import get_db_connection

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Dashboard"])

ADMIN_PASSCODE = os.getenv("ADMIN_PASSCODE", "admin1234")

# โหลด Access Token สำหรับแต่ละบริษัท (มี Fallback ให้ TP Extra)
COMPANY_TOKENS = {
    "tp_extra": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_TP_EXTRA"),
    "pro_nexus": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_PRO_NEXUS"),
    "luck_kio": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_LUCK_KIO"),
    "peak_icon": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_PEAK_ICON")
}

class LoginRequest(BaseModel):
    passcode: str

class UpdateOrderStatusRequest(BaseModel):
    status: str = Field(..., example="shipping")
    tracking_number: Optional[str] = None

def verify_admin(x_admin_key: Optional[str] = Header(None)):
    if not x_admin_key or x_admin_key != ADMIN_PASSCODE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="รหัสผ่านผู้ดูแลระบบไม่ถูกต้องหรือไม่ได้รับอนุญาต"
        )

def send_line_push_notification(company_slug: str, line_user_id: str, message_text: str):
    """ส่ง Push Message หาผู้ใช้ผ่าน LINE Messaging API"""
    token = COMPANY_TOKENS.get(company_slug)
    if not token or line_user_id.startswith("U_GUEST"):
        return
    try:
        conf = Configuration(access_token=token)
        with ApiClient(conf) as api_client:
            line_api = MessagingApi(api_client)
            line_api.push_message(
                PushMessageRequest(
                    to=line_user_id,
                    messages=[TextMessage(text=message_text)]
                )
            )
    except Exception as e:
        print(f"⚠️ ไม่สามารถส่ง LINE Push Message: {e}")

@router.post("/verify-passcode")
def verify_passcode(payload: LoginRequest):
    if payload.passcode == ADMIN_PASSCODE:
        return {"status": "success", "token": ADMIN_PASSCODE}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passcode ไม่ถูกต้อง")

@router.get("/overview")
def get_dashboard_overview(company: str = Query(default="tp_extra"), x_admin_key: Optional[str] = Header(None)):
    verify_admin(x_admin_key)
    
    stats_query = """
        SELECT 
            COUNT(CASE WHEN status = 'paid' THEN 1 END) AS paid_orders,
            COUNT(CASE WHEN status = 'pending_payment' THEN 1 END) AS pending_orders,
            COUNT(CASE WHEN status = 'shipping' THEN 1 END) AS shipping_orders,
            COALESCE(SUM(CASE WHEN status = 'paid' THEN total_amount ELSE 0 END), 0) AS total_revenue
        FROM orders
        WHERE company_slug = %s;
    """
    recent_orders_query = """
        SELECT o.order_no, o.line_user_id, o.customer_name, o.customer_phone, o.shipping_address, CAST(o.total_amount AS FLOAT) AS total_amount, o.status, 
               s.image_url AS slip_url, CAST(s.trans_amount AS FLOAT) AS slip_amount,
               DATE_FORMAT(o.created_at, '%d/%m/%Y %H:%i') AS created_at
        FROM orders o
        LEFT JOIN slips s ON o.slip_id = s.id
        WHERE o.company_slug = %s
        ORDER BY o.id DESC LIMIT 50;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(stats_query, (company,))
                stats = cursor.fetchone()
                
                cursor.execute(recent_orders_query, (company,))
                orders = cursor.fetchall()

        return {"status": "success", "stats": stats, "orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/orders/{order_no}/status")
def update_order_status(order_no: str, payload: UpdateOrderStatusRequest, x_admin_key: Optional[str] = Header(None)):
    verify_admin(x_admin_key)

    valid_statuses = ["pending_payment", "paid", "shipping", "completed", "cancelled"]
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    find_order_sql = "SELECT line_user_id, company_slug, total_amount FROM orders WHERE order_no = %s;"
    update_sql = "UPDATE orders SET status = %s, updated_at = NOW() WHERE order_no = %s;"

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(find_order_sql, (order_no,))
                order = cursor.fetchone()
                if not order:
                    raise HTTPException(status_code=404, detail="Order not found")

                cursor.execute(update_sql, (payload.status, order_no))
            conn.commit()

        # ส่ง Push Notification ไปยัง LINE ลูกค้าตามสถานะใหม่
        if payload.status == "shipping":
            track_txt = f"\n📦 เลขพัสดุ: {payload.tracking_number}" if payload.tracking_number else ""
            msg = f"🚚 สินค้าของคุณกำลังจัดส่ง!\n\nรหัสออเดอร์: {order_no}{track_txt}\nขอบคุณที่อุดหนุนสินค้า BAENGPUN แบ่งปันชอป ครับ"
            send_line_push_notification(order["company_slug"], order["line_user_id"], msg)

        elif payload.status == "completed":
            msg = f"🎉 คำสั่งซื้อ {order_no} จัดส่งสำเร็จเรียบร้อยแล้ว\nหวังว่าจะประทับใจในสินค้าของเราครับ"
            send_line_push_notification(order["company_slug"], order["line_user_id"], msg)

        return {"status": "success", "order_no": order_no, "new_status": payload.status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BatchStatusUpdateRequest(BaseModel):
    order_nos: list[str]
    status: str
    tracking_prefix: Optional[str] = None

@router.post("/orders/batch-status")
def batch_update_order_status(
    payload: BatchStatusUpdateRequest,
    admin_key: str = Depends(verify_admin_key)
):
    if not payload.order_nos:
        raise HTTPException(status_code=400, detail="No orders provided")

    format_strings = ",".join(["%s"] * len(payload.order_nos))
    update_sql = f"""
        UPDATE orders
        SET status = %s, updated_at = NOW()
        WHERE order_no IN ({format_strings});
    """
    params = [payload.status] + payload.order_nos

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(update_sql, params)
                affected = cursor.rowcount
            conn.commit()
        return {
            "status": "success",
            "message": f"Updated {affected} orders to {payload.status}",
            "affected_rows": affected
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
