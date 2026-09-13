from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
import uuid

router = APIRouter()

class CreateDeliveryModel(BaseModel):
    order_ref: str
    customer_name: str
    customer_phone: str
    delivery_address: str
    latitude: float
    longitude: float
    preferred_provider: str = 'in_house' # in_house, lalamove, grab

class RiderUpdateStatusModel(BaseModel):
    delivery_id: int
    rider_id: str
    status: str # accepted, picked_up, delivered

@router.post("/logistics/delivery/create")
def create_delivery_job(job: CreateDeliveryModel, tenant_id: str = Depends(verify_tenant_header)):
    """
    (7.1) สร้างงานจัดส่ง หากเลือก in_house ระบบจะกระจายงานให้ Rider ในพื้นที่
    หากเลือก Lalamove/Grab ระบบจะยิง API ไปเรียกคนขับภายนอก
    """
    conn = get_db_connection()
    try:
        tracking_url = None
        delivery_fee = 0.0
        rider_name = None
        
        # 1. จำลองการยิง API ไป Lalamove / Grab (3rd Party Integration)
        if job.preferred_provider == 'lalamove':
            # MOCK: lalamove_api.request_vehicle(...)
            delivery_fee = 120.00 # สมมติว่าดึงราคามาได้ 120 บาท
            tracking_url = f"https://track.lalamove.com/{uuid.uuid4().hex[:10]}"
            rider_name = "Lalamove Driver (Pending)"
        elif job.preferred_provider == 'grab':
            # MOCK: grab_express_api.book(...)
            delivery_fee = 95.00
            tracking_url = f"https://express.grab.com/track/{uuid.uuid4().hex[:10]}"
            rider_name = "Grab Driver (Pending)"
        else:
            # In-house: คำนวณระยะทางจากร้านถึงลูกค้า (จำลอง กม. ละ 10 บาท)
            delivery_fee = 35.00 
            tracking_url = f"https://pronexus.app/track/{tenant_id}/{job.order_ref}"

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO delivery_orders (
                    tenant_id, order_ref, customer_name, customer_phone, delivery_address,
                    latitude, longitude, delivery_fee, provider, rider_name, tracking_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (tenant_id, job.order_ref, job.customer_name, job.customer_phone, job.delivery_address, 
                  job.latitude, job.longitude, delivery_fee, job.preferred_provider, rider_name, tracking_url))
            delivery_id = cursor.lastrowid
            
        conn.commit()
        return {
            "status": "success",
            "delivery_id": delivery_id,
            "provider": job.preferred_provider,
            "delivery_fee": delivery_fee,
            "tracking_url": tracking_url,
            "message": f"ส่งคำสั่งจัดส่งผ่าน {job.preferred_provider} เรียบร้อยแล้ว"
        }
    finally:
        conn.close()

@router.put("/logistics/delivery/rider-update")
def update_delivery_status(update_data: RiderUpdateStatusModel, tenant_id: str = Depends(verify_tenant_header)):
    """(7.1) API สำหรับ Rider App (In-house) เวลากดรับงาน หรือส่งของเสร็จ"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT status FROM delivery_orders WHERE id = %s AND tenant_id = %s", (update_data.delivery_id, tenant_id))
            order = cursor.fetchone()
            
            if not order:
                raise HTTPException(status_code=404, detail="ไม่พบออเดอร์จัดส่งนี้")
                
            if update_data.status == 'accepted' and order['status'] != 'finding_rider':
                raise HTTPException(status_code=400, detail="ออเดอร์นี้มีคนขับรับไปแล้ว")
                
            cursor.execute("""
                UPDATE delivery_orders SET status = %s, rider_id = %s 
                WHERE id = %s
            """, (update_data.status, update_data.rider_id, update_data.delivery_id))
            
        conn.commit()
        return {"status": "success", "message": f"อัปเดตสถานะเป็น {update_data.status} สำเร็จ"}
    finally:
        conn.close()
