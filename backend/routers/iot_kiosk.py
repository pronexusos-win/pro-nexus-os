from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
import uuid

router = APIRouter()

class KioskOrder(BaseModel):
    kiosk_id: str
    sku: str
    slot_number: str
    customer_id: str
    price: float

@router.get("/kiosk/scan/{kiosk_id}")
def scan_kiosk(kiosk_id: str, tenant_id: str = Depends(verify_tenant_header)):
    """ลูกค้าสแกน QR หน้าตู้: ดึงสถานะตู้และสต็อกสินค้าแบบเรียลไทม์"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # เช็กสถานะตู้
            cursor.execute("SELECT status, type FROM kiosk_machines WHERE kiosk_id = %s AND tenant_id = %s", (kiosk_id, tenant_id))
            machine = cursor.fetchone()
            
            if not machine or machine['status'] != 'online':
                raise HTTPException(status_code=400, detail="ตู้ปิดให้บริการชั่วคราว หรือกำลังซ่อมบำรุง")
                
            # ดึงสต็อกสินค้าในตู้นั้น
            cursor.execute("""
                SELECT sku, product_name, price, stock_quantity, slot_number 
                FROM kiosk_inventory 
                WHERE kiosk_id = %s AND stock_quantity > 0
            """, (kiosk_id,))
            items = cursor.fetchall()
            
        return {"status": "success", "machine_type": machine['type'], "available_items": items}
    finally:
        conn.close()

@router.post("/kiosk/dispense")
def dispense_product(order: KioskOrder, tenant_id: str = Depends(verify_tenant_header)):
    """ลูกค้ายืนยันจ่ายเงิน: ตัดสต็อกและส่งสัญญาณเปิดตู้"""
    # หมายเหตุ: ในระบบจริงจะมีการหักเงินจาก Wallet ก่อน
    transaction_id = str(uuid.uuid4())
    
    # 1. โค้ดส่งสัญญาณ MQTT ไปที่ตู้ (Simulated)
    mqtt_topic = f"pronexus/kiosk/{tenant_id}/{order.kiosk_id}/command"
    mqtt_payload = {"cmd": "dispense", "slot": order.slot_number, "tx_id": transaction_id}
    # mqtt_client.publish(mqtt_topic, json.dumps(mqtt_payload))
    
    return {
        "status": "processing",
        "message": "ส่งคำสั่งจ่ายสินค้าไปยังตู้เรียบร้อย กรุณารอรับสินค้า",
        "transaction_id": transaction_id,
        "mqtt_topic_published": mqtt_topic
    }

@router.post("/kiosk/webhook/sensor-feedback")
def sensor_feedback(tx_id: str, status: str, kiosk_id: str):
    """Webhook รับสัญญาณจากเซ็นเซอร์ตู้ ว่าของตกจริงไหม ถ้า Error ให้คืนเงินอัตโนมัติ"""
    if status == 'error_jammed':
        # ตรรกะคืนเงิน (Auto-Refund) กลับเข้า Wallet ลูกค้า
        return {"status": "refunded", "message": "ระบบขัดข้อง คืนแต้มให้ลูกค้าเรียบร้อยแล้ว"}
    return {"status": "completed", "message": "จ่ายสินค้าสำเร็จ หักภาษีและจ่ายคอมมิชชันเข้าระบบ"}
