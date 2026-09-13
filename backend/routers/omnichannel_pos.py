from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

class OrderItem(BaseModel):
    sku: str
    quantity: int

class CheckoutRequest(BaseModel):
    channel: str # 'storefront', 'mobile_pos', 'line_oa', 'marketplace'
    customer_tier: str = 'retail' # 'retail', 'wholesale_partner', 'vip'
    items: List[OrderItem]

@router.post("/pos/checkout")
def multi_channel_checkout(order: CheckoutRequest, tenant_id: str = Depends(verify_tenant_header)):
    """
    ระบบคิดเงินรวมศูนย์: ตัดสต็อกและคำนวณราคาตามช่องทางและระดับลูกค้า (Wholesale/Retail)
    """
    conn = get_db_connection()
    try:
        total_amount = 0.0
        processed_items = []
        
        with conn.cursor() as cursor:
            for item in order.items:
                # 1. ดึงราคาสินค้า (เช็กราคาตาม 8 ระดับ และ จำนวนขั้นต่ำ MOQ)
                cursor.execute("""
                    SELECT price_retail, price_wholesale_1, price_wholesale_2, moq_wholesale_1, moq_wholesale_2, stock_quantity
                    FROM products 
                    WHERE tenant_id = %s AND sku = %s
                """, (tenant_id, item.sku))
                product = cursor.fetchone()
                
                if not product or product['stock_quantity'] < item.quantity:
                    raise HTTPException(status_code=400, detail=f"สินค้า SKU {item.sku} มีสต็อกไม่เพียงพอ")
                
                # 2. ตรรกะคำนวณราคาขายส่ง (Wholesale Logic)
                unit_price = product['price_retail']
                if item.quantity >= product['moq_wholesale_2'] or order.customer_tier == 'vip':
                    unit_price = product['price_wholesale_2']
                elif item.quantity >= product['moq_wholesale_1'] or order.customer_tier == 'wholesale_partner':
                    unit_price = product['price_wholesale_1']
                    
                line_total = unit_price * item.quantity
                total_amount += line_total
                
                # 3. ตัดสต็อกคลังสินค้าส่วนกลาง
                cursor.execute("""
                    UPDATE products SET stock_quantity = stock_quantity - %s 
                    WHERE tenant_id = %s AND sku = %s
                """, (item.quantity, tenant_id, item.sku))
                
                processed_items.append({
                    "sku": item.sku,
                    "quantity": item.quantity,
                    "unit_price_applied": unit_price,
                    "line_total": line_total
                })
                
        conn.commit()
        return {
            "status": "success",
            "channel": order.channel,
            "total_amount": total_amount,
            "items": processed_items,
            "message": "บันทึกยอดขายและตัดสต็อกส่วนกลางสำเร็จ"
        }
    finally:
        conn.close()
