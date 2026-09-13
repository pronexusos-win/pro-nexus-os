from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

class ScanRequest(BaseModel):
    barcode: str

@router.post("/sales/scan-barcode")
def scan_barcode_to_cart(scan: ScanRequest, tenant_id: str = Depends(verify_tenant_header)):
    """
    (8.4) รับบาร์โค้ดจากเครื่องสแกน ค้นหาสินค้า เช็กสต็อก และดึงราคามาใส่ตะกร้า
    รองรับทั้งการยิง SKU ตรงๆ หรือ Barcode สากล (EAN-13 / UPC)
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ค้นหาสินค้าจาก SKU หรือ Barcode
            cursor.execute("""
                SELECT p.sku, p.product_name, p.price_retail, p.tax_type,
                       COALESCE(w.stock_quantity, 0) as stock_quantity
                FROM products p
                LEFT JOIN warehouse_inventory w ON p.sku = w.sku AND p.tenant_id = w.tenant_id
                WHERE p.tenant_id = %s AND (p.sku = %s OR p.barcode = %s)
            """, (tenant_id, scan.barcode, scan.barcode))
            product = cursor.fetchone()
            
            if not product:
                raise HTTPException(status_code=404, detail=f"ไม่พบสินค้าจากบาร์โค้ด: {scan.barcode}")
                
            if product['stock_quantity'] <= 0:
                raise HTTPException(status_code=400, detail=f"สินค้า '{product['product_name']}' สต็อกหมดแล้ว!")
                
        return {
            "status": "success",
            "product": {
                "sku": product['sku'],
                "product_name": product['product_name'],
                "unit_price": float(product['price_retail']),
                "tax_type": product['tax_type'],
                "current_stock": product['stock_quantity']
            },
            "message": "สแกนสินค้าเข้าตะกร้าสำเร็จ"
        }
    finally:
        conn.close()
