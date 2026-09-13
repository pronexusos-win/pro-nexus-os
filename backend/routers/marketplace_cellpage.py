from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
from datetime import datetime, timedelta
import uuid

router = APIRouter()

class QRGenerateModel(BaseModel):
    action_type: str
    amount: float = None
    ttl_minutes: int = 15

@router.get("/marketplace/shop/{slug}")
def get_shop_cellpage(slug: str):
    """
    (9.1) ดึงข้อมูลหน้าร้าน Cell Page (ไม่ต้องล๊อกอินก็ดูได้ เพื่อการทำ SEO)
    แสดงสถานะ เปิด/ปิด แผนที่ และเมนู
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM cell_pages WHERE slug = %s", (slug,))
            shop = cursor.fetchone()
            if not shop:
                raise HTTPException(status_code=404, detail="ไม่พบหน้า Cell Page ของร้านนี้")
                
            # ดึงรายการสินค้าของร้านนี้ที่เปิดขายออนไลน์ (เฉพาะสินค้าที่เปิดใช้งาน)
            cursor.execute("SELECT sku, product_name, price_retail, cover_image FROM products WHERE tenant_id = %s AND is_active = TRUE", (shop['tenant_id'],))
            products = cursor.fetchall()
            
        return {
            "status": "success",
            "shop_info": shop,
            "products": products
        }
    finally:
        conn.close()

@router.post("/marketplace/qr/generate")
def generate_dynamic_qr(req: QRGenerateModel, tenant_id: str = Depends(verify_tenant_header)):
    """
    (9.1) สร้าง Dynamic QR Code เช่น สแกนจ่ายค่าหมูตามน้ำหนัก หรือ สแกนดูเมนู
    """
    conn = get_db_connection()
    try:
        qr_id = f"QR-{uuid.uuid4().hex[:12].upper()}"
        expires_at = datetime.now() + timedelta(minutes=req.ttl_minutes)
        
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO dynamic_qr_codes (id, tenant_id, action_type, amount, expires_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (qr_id, tenant_id, req.action_type, req.amount, expires_at))
            
        conn.commit()
        
        # คืนค่า URL ที่เอาไปให้ Frontend สร้างรูป QR Code
        scan_url = f"https://pronexus.app/scan/{qr_id}"
        
        return {
            "status": "success",
            "qr_id": qr_id,
            "scan_url": scan_url,
            "amount": req.amount,
            "expires_at": expires_at
        }
    finally:
        conn.close()
