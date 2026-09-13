from fastapi import APIRouter, Depends, HTTPException
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

@router.get("/procurement/transit-stock")
def get_all_transit_stock(tenant_id: str = Depends(verify_tenant_header)):
    """
    รายงานสินค้าระหว่างทาง (Transit Stock Report) สำหรับหลังบ้าน
    ดึงข้อมูลจาก PO ที่ยังรับของไม่ครบทั้งหมด
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    po.po_number,
                    po.supplier_id,
                    poi.sku,
                    (poi.order_qty - poi.received_qty) AS transit_qty,
                    po.created_at AS order_date
                FROM purchase_orders po
                JOIN po_items poi ON po.id = poi.po_id
                WHERE po.tenant_id = %s 
                  AND po.status IN (1, 2) 
                  AND (poi.order_qty - poi.received_qty) > 0
                ORDER BY po.created_at ASC
            """, (tenant_id,))
            transit_items = cursor.fetchall()
            
        return {
            "status": "success", 
            "total_transit_items": len(transit_items),
            "transit_stock": transit_items
        }
    finally:
        conn.close()

@router.get("/procurement/transit-stock/{sku}")
def get_transit_stock_by_sku(sku: str, tenant_id: str = Depends(verify_tenant_header)):
    """
    เช็กสินค้าระหว่างทางรายชิ้น (สำหรับหน้าจอ POS / แคชเชียร์)
    เพื่อให้แคชเชียร์ตอบลูกค้าได้ทันทีว่าของกำลังมาส่งกี่ชิ้น
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT SUM(poi.order_qty - poi.received_qty) AS total_incoming
                FROM purchase_orders po
                JOIN po_items poi ON po.id = poi.po_id
                WHERE po.tenant_id = %s 
                  AND po.status IN (1, 2)
                  AND poi.sku = %s
            """, (tenant_id, sku))
            result = cursor.fetchone()
            
            # ถ้าเป็น None แปลว่าไม่มีการสั่งของรอดำเนินการอยู่
            total_incoming = int(result['total_incoming']) if result['total_incoming'] else 0
            
        return {
            "status": "success", 
            "sku": sku, 
            "incoming_qty": total_incoming,
            "message": f"สินค้ารหัส {sku} กำลังเดินทางมา {total_incoming} ชิ้น"
        }
    finally:
        conn.close()
