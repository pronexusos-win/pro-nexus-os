from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

class CommunityPost(BaseModel):
    author_id: str
    post_type: str # 'sell' (ขายของ), 'buy' (รับซื้อ), 'ride' (เรียกรถ/ส่งของ)
    title: str
    details: str
    price: Optional[float] = 0.0

class PreOrderRequest(BaseModel):
    vendor_id: str  # รหัสพนักงาน/รถเร่
    customer_id: str
    sku: str
    quantity: int

@router.post("/community/post")
def create_post(post: CommunityPost, tenant_id: str = Depends(verify_tenant_header)):
    """สร้างโพสต์ประกาศในตลาดชุมชน (เช่น ยายสีขายผักบุ้ง, ยายสีเรียกวิน)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO community_posts (tenant_id, author_id, post_type, title, details, price, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'active')
            """, (tenant_id, post.author_id, post.post_type, post.title, post.details, post.price))
        conn.commit()
        return {"status": "success", "message": "โพสต์ประกาศลงตลาดนัดชุมชนสำเร็จ"}
    finally:
        conn.close()

@router.put("/community/match/{post_id}")
def match_post(post_id: int, responder_id: str, tenant_id: str = Depends(verify_tenant_header)):
    """คนในชุมชนกดรับงาน หรือกดซื้อของ (เช่น ตามีกดรับงานวินยายสี)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ล็อกสถานะเป็น in_progress เพื่อไม่ให้คนอื่นกดซ้ำ
            affected = cursor.execute("""
                UPDATE community_posts 
                SET status = 'in_progress', matched_with = %s 
                WHERE id = %s AND tenant_id = %s AND status = 'active'
            """, (responder_id, post_id, tenant_id))
            
            if affected == 0:
                raise HTTPException(status_code=400, detail="โพสต์นี้ถูกรับงานไปแล้ว หรือถูกปิดไปแล้ว")
        conn.commit()
        return {"status": "success", "message": "จับคู่งานสำเร็จ เริ่มดำเนินการได้เลย"}
    finally:
        conn.close()

@router.post("/vendor/pre-order")
def reserve_vendor_stock(order: PreOrderRequest, tenant_id: str = Depends(verify_tenant_header)):
    """ระบบจองสินค้าล่วงหน้าจากรถเร่ (ตามีจองต้มยำกุ้งตาหมาย)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. เช็กสต็อกในคลังย่อยของรถเร่คันนั้น
            cursor.execute("""
                SELECT stock_quantity FROM mobile_vendor_inventory 
                WHERE vendor_id = %s AND sku = %s AND tenant_id = %s
            """, (order.vendor_id, order.sku, tenant_id))
            stock = cursor.fetchone()
            
            if not stock or stock['stock_quantity'] < order.quantity:
                raise HTTPException(status_code=400, detail="สินค้าบนรถเร่หมด หรือมีไม่พอให้จอง")
                
            # 2. ตัดสต็อกทันทีเพื่อล็อกของไว้ให้คนจอง (กันขายซ้ำหน้าร้าน)
            cursor.execute("""
                UPDATE mobile_vendor_inventory 
                SET stock_quantity = stock_quantity - %s 
                WHERE vendor_id = %s AND sku = %s AND tenant_id = %s
            """, (order.quantity, order.vendor_id, order.sku, tenant_id))
            
            # 3. บันทึกใบจอง
            cursor.execute("""
                INSERT INTO pre_orders (tenant_id, vendor_id, customer_id, sku, quantity, status)
                VALUES (%s, %s, %s, %s, %s, 'reserved')
            """, (tenant_id, order.vendor_id, order.customer_id, order.sku, order.quantity))
            
        conn.commit()
        return {"status": "success", "message": "จองสินค้าสำเร็จ สินค้าถูกล็อกไว้รอคุณมารับแล้ว"}
    finally:
        conn.close()
