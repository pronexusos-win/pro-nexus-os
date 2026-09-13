from fastapi import APIRouter, Depends, HTTPException
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

@router.get("/scan/{barcode}")
def scan_barcode(barcode: str, role: str = "cashier", tenant_id: str = Depends(verify_tenant_header)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT barcode, product_id, product_name, retail_price, cost_price, stock_qty 
                FROM store_inventory WHERE barcode = %s AND tenant_id = %s
            """, (barcode, tenant_id))
            item = cursor.fetchone()
            
            if not item:
                raise HTTPException(status_code=404, detail="ไม่พบสินค้าจากบาร์โค้ดนี้")
                
            # ปิดบังข้อมูลต้นทุนถ้าไม่ใช่ระดับผู้บริหาร (Super Admin / Company Admin)
            if role not in ["super_admin", "company_admin"]:
                item.pop("cost_price", None)
                
        return {"status": "success", "item": item}
    finally:
        conn.close()
