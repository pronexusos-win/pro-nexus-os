from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
from datetime import datetime

router = APIRouter()

class CartItemModel(BaseModel):
    sku: str
    quantity: int
    unit_price: float

class CalculateCartModel(BaseModel):
    promo_code: Optional[str] = None
    items: List[CartItemModel]

@router.post("/sales/calculate-cart")
def calculate_cart_with_promotion(cart: CalculateCartModel, tenant_id: str = Depends(verify_tenant_header)):
    """
    (2.3) คำนวณยอดตะกร้าสินค้า พร้อมหักส่วนลดรายชิ้น หรือส่วนลดท้ายบิล 
    รองรับทั้งแบบลดเป็นเปอร์เซ็นต์ (%) และลดเป็นจำนวนเงิน (บาท)
    """
    conn = get_db_connection()
    try:
        subtotal = 0.0
        processed_items = []
        
        # 1. คำนวณยอดรวมพื้นฐานก่อน (Subtotal)
        for item in cart.items:
            line_total = item.quantity * item.unit_price
            subtotal += line_total
            processed_items.append({
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "original_line_total": line_total,
                "discount_amount": 0.0,
                "net_line_total": line_total
            })
            
        bill_discount = 0.0
        applied_promo_name = None

        # 2. ตรวจสอบและคำนวณโปรโมชัน (ถ้ามีการส่งโค้ดมา)
        if cart.promo_code:
            with conn.cursor() as cursor:
                now = datetime.now()
                cursor.execute("""
                    SELECT * FROM promotions 
                    WHERE tenant_id = %s AND promo_code = %s AND is_active = TRUE
                """, (tenant_id, cart.promo_code))
                promo = cursor.fetchone()
                
                if not promo:
                    raise HTTPException(status_code=400, detail="ไม่พบโค้ดส่วนลดนี้ หรือโค้ดถูกระงับการใช้งาน")
                    
                if promo['start_date'] and now < promo['start_date'] or promo['end_date'] and now > promo['end_date']:
                    raise HTTPException(status_code=400, detail="โค้ดส่วนลดนี้หมดอายุหรือไม่ครอบคลุมช่วงเวลาปัจจุบัน")
                    
                if subtotal < promo['min_purchase_amount']:
                    raise HTTPException(status_code=400, detail=f"ยอดซื้อขั้นต่ำไม่ถึงเงื่อนไข (ต้องซื้ออย่างน้อย {promo['min_purchase_amount']} บาท)")
                
                applied_promo_name = promo['promo_name']
                
                # ตรรกะ: ลดท้ายบิล (Bill-Level)
                if promo['apply_level'] == 'bill':
                    if promo['discount_type'] == 'percent':
                        bill_discount = subtotal * (promo['discount_value'] / 100)
                    elif promo['discount_type'] == 'amount':
                        bill_discount = float(promo['discount_value'])
                        
                    # กันส่วนลดเกินยอดซื้อ
                    bill_discount = min(bill_discount, subtotal)
                
                # ตรรกะ: ลดเฉพาะชิ้น (Item-Level)
                elif promo['apply_level'] == 'item':
                    for p_item in processed_items:
                        if p_item['sku'] == promo['target_sku']:
                            if promo['discount_type'] == 'percent':
                                item_disc = p_item['original_line_total'] * (promo['discount_value'] / 100)
                            elif promo['discount_type'] == 'amount':
                                # หักตามจำนวนชิ้น เช่น ลดชิ้นละ 10 บาท ซื้อ 3 ชิ้น ลด 30 บาท
                                item_disc = float(promo['discount_value']) * p_item['quantity']
                                
                            item_disc = min(item_disc, p_item['original_line_total'])
                            p_item['discount_amount'] = item_disc
                            p_item['net_line_total'] = p_item['original_line_total'] - item_disc
                            
                            # คำนวณ Subtotal ใหม่
                            subtotal = sum(i['net_line_total'] for i in processed_items)

        # 3. สรุปยอด
        grand_total = subtotal - bill_discount
        
        return {
            "status": "success",
            "summary": {
                "subtotal": round(sum(i['original_line_total'] for i in processed_items), 2),
                "total_item_discount": round(sum(i['discount_amount'] for i in processed_items), 2),
                "bill_discount": round(bill_discount, 2),
                "grand_total": round(grand_total, 2),
                "applied_promo": applied_promo_name
            },
            "items": processed_items
        }
    finally:
        conn.close()
