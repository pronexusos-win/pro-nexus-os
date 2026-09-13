from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.database import get_db_connection

router = APIRouter()

class SalesTransaction(BaseModel):
    order_ref: str
    buyer_id: str
    total_sales_amount: float

def distribute_80_20(cursor, user_id: str, raw_commission: float, order_ref: str, level_note: str):
    """ฟังก์ชันสับแต้ม 80/20 และโอนเข้ากระเป๋า"""
    cash_pt = raw_commission * 0.80
    shop_pt = raw_commission * 0.20
    
    # อัปเดตกระเป๋าเงิน
    cursor.execute("""
        INSERT INTO tpx_wallets (user_id, cash_point, shopping_point) 
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        cash_point = cash_point + %s, shopping_point = shopping_point + %s
    """, (user_id, cash_pt, shop_pt, cash_pt, shop_pt))
    
    # บันทึกประวัติ (เพื่อแสดงในหน้าเมนู Point)
    cursor.execute("""
        INSERT INTO wallet_transactions (tenant_id, user_id, ref_doc, trans_type, direction, amount, note)
        VALUES 
        ('tp_extra', %s, %s, 'CASH_PT', 'IN', %s, %s),
        ('tp_extra', %s, %s, 'SHOP_PT', 'IN', %s, %s)
    """, (user_id, order_ref, cash_pt, f"{level_note} (80%)", user_id, order_ref, shop_pt, f"{level_note} (20%)"))

@router.post("/tpx/commission/process")
def process_tpx_commission(sale: SalesTransaction):
    """คำนวณจ่าย 1% ให้ผู้ซื้อ และ 1% ขึ้นไปหา Upline 4 ชั้น"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            base_comm = sale.total_sales_amount * 0.01 # 1% ของยอดขาย
            
            # 1. จ่าย Cashback 1% ให้ผู้ซื้อ (ตัวเอง)
            distribute_80_20(cursor, sale.buyer_id, base_comm, sale.order_ref, "Cashback ซื้อส่วนตัว")
            
            # 2. ค้นหา Upline 4 ชั้น และจ่ายชั้นละ 1%
            current_user = sale.buyer_id
            for level in range(1, 5):
                cursor.execute("SELECT sponsor_id FROM tpx_unilevel_tree WHERE user_id = %s", (current_user,))
                result = cursor.fetchone()
                
                if not result or not result['sponsor_id']:
                    break # ถ้าสายงานขาด หรือไม่มีผู้แนะนำ ให้หยุดแค่นี้ (ส่วนต่างที่เหลือตีเข้าบริษัท)
                    
                upline_id = result['sponsor_id']
                distribute_80_20(cursor, upline_id, base_comm, sale.order_ref, f"โบนัสเครือข่าย ชั้นที่ {level}")
                
                # ขยับขึ้นไปหา Upline ชั้นต่อไป
                current_user = upline_id 
                
        conn.commit()
        return {"status": "success", "message": "คำนวณและกระจายคอมมิชชัน 5 ชั้น พร้อมสับ 80/20 เสร็จสมบูรณ์"}
    finally:
        conn.close()
