from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

# --- โครงสร้างข้อมูลสำหรับ รถเร่ / POS ออฟไลน์ ---
class OfflineCartItem(BaseModel):
    barcode: str
    product_name: str
    price_per_kg: float
    weight_kg: float  # น้ำหนักที่ชั่งได้ หรือให้ลูกค้าใส่เอง

@router.post("/offline/calculate-weight-sale")
def calculate_weight_sale(item: OfflineCartItem, tenant_id: str = Depends(verify_tenant_header)):
    """คำนวณราคาสินค้าชั่งน้ำหนัก สำหรับรถเร่ หรือให้ลูกค้าสแกนคีย์น้ำหนักเอง"""
    total_price = round(item.price_per_kg * item.weight_kg, 2)
    return {
        "status": "success",
        "product_name": item.product_name,
        "price_per_kg": item.price_per_kg,
        "weight_kg": item.weight_kg,
        "total_price": total_price,
        "message": "คำนวณราคาเรียบร้อย พร้อมพิมพ์ใบเสร็จหรือชำระเงิน"
    }

# --- โครงสร้างข้อมูลสำหรับ ร้านอาหาร 4 จอ ---
class RestaurantOrderCreate(BaseModel):
    table_number: str
    items: list
    customer_id: Optional[str] = None

@router.post("/restaurant/order")
def create_restaurant_order(order: RestaurantOrderCreate, tenant_id: str = Depends(verify_tenant_header)):
    """จอลูกค้า: สแกนโต๊ะ กดสั่งอาหาร ส่งเข้าจอครัวอัตโนมัติ"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # บันทึกออเดอร์ลงฐานข้อมูลร้านอาหาร
            cursor.execute("""
                INSERT INTO restaurant_orders (tenant_id, table_number, items, status, customer_id)
                VALUES (%s, %s, %s, 'pending_kitchen', %s)
            """, (tenant_id, order.table_number, str(order.items), order.customer_id))
            order_id = cursor.lastrowid
        conn.commit()
        return {
            "status": "success",
            "order_id": order_id,
            "table_number": order.table_number,
            "message": "สั่งอาหารสำเร็จ ส่งออเดอร์ไปที่ครัวและพนักงานเสิร์ฟเรียบร้อย!"
        }
    finally:
        conn.close()

@router.get("/restaurant/kitchen/orders")
def get_kitchen_orders(tenant_id: str = Depends(verify_tenant_header)):
    """จอครัว: ดึงออเดอร์ที่ค้างทำทั้งหมด"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT order_id, table_number, items, status, created_at 
                FROM restaurant_orders 
                WHERE tenant_id = %s AND status IN ('pending_kitchen', 'cooking')
            """, (tenant_id,))
            orders = cursor.fetchall()
        return {"status": "success", "orders": orders}
    finally:
        conn.close()

@router.put("/restaurant/order/status/{order_id}")
def update_order_status(order_id: int, status: str, tenant_id: str = Depends(verify_tenant_header)):
    """อัปเดตสถานะออเดอร์ (ครัวทำเสร็จ -> รอเสิร์ฟ -> เสิร์ฟแล้ว -> จ่ายเงินแล้ว)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE restaurant_orders SET status = %s WHERE order_id = %s AND tenant_id = %s
            """, (status, order_id, tenant_id))
        conn.commit()
        return {"status": "success", "message": f"อัปเดตสถานะออเดอร์ #{order_id} เป็น '{status}' เรียบร้อย"}
    finally:
        conn.close()
