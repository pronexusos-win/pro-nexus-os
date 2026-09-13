from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
from datetime import datetime

router = APIRouter()

class ScanItemModel(BaseModel):
    tracking_no: str
    sku: str
    packer_id: str

@router.get("/fulfillment/order/{tracking_no}")
def load_order_for_packing(tracking_no: str, tenant_id: str = Depends(verify_tenant_header)):
    """(5.1) สแกน Tracking ID หน้ากล่อง เพื่อดึงรายการสินค้าที่ต้องแพ็คขึ้นจอ"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, status, customer_name FROM fulfillment_orders WHERE tenant_id = %s AND tracking_no = %s", (tenant_id, tracking_no))
            order = cursor.fetchone()
            
            if not order:
                raise HTTPException(status_code=404, detail="ไม่พบหมายเลข Tracking นี้ในระบบ")
            if order['status'] in ['packed', 'shipped']:
                raise HTTPException(status_code=400, detail="ออเดอร์นี้ถูกแพ็คหรือจัดส่งไปแล้ว")
                
            # เปลี่ยนสถานะเป็นกำลังแพ็ค
            if order['status'] == 'pending':
                cursor.execute("UPDATE fulfillment_orders SET status = 'packing' WHERE id = %s", (order['id'],))
                conn.commit()

            cursor.execute("SELECT sku, required_qty, packed_qty FROM fulfillment_items WHERE order_id = %s", (order['id'],))
            items = cursor.fetchall()
            
        return {"status": "success", "tracking_no": tracking_no, "customer": order['customer_name'], "items": items}
    finally:
        conn.close()

@router.post("/fulfillment/scan-item")
def scan_item_to_pack(scan: ScanItemModel, tenant_id: str = Depends(verify_tenant_header)):
    """
    (5.2 & 5.3) สแกนบาร์โค้ดสินค้าทีละชิ้นลงกล่อง
    - มีระบบ Error Prevention กันสแกนผิด SKU และสแกนเกินจำนวน
    - หากสแกนครบ ระบบจะส่ง Trigger สั่งพิมพ์ Label อัตโนมัติ
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. หา Order ID
            cursor.execute("SELECT id, status FROM fulfillment_orders WHERE tenant_id = %s AND tracking_no = %s", (tenant_id, scan.tracking_no))
            order = cursor.fetchone()
            if not order or order['status'] == 'packed':
                return {"status": "error", "error_type": "invalid_order", "message": "ออเดอร์ไม่ถูกต้อง หรือถูกแพ็คเสร็จไปแล้ว"}

            order_id = order['id']

            # 2. เช็กว่า SKU นี้อยู่ในออเดอร์ไหม (Error Prevention: สแกนผิดของ)
            cursor.execute("SELECT id, required_qty, packed_qty FROM fulfillment_items WHERE order_id = %s AND sku = %s", (order_id, scan.sku))
            item = cursor.fetchone()
            
            if not item:
                return {"status": "error", "error_type": "wrong_sku", "message": f"ตี๊ดดด! สินค้ารหัส {scan.sku} ไม่ได้อยู่ในออเดอร์นี้!"}
                
            # 3. เช็กว่าสแกนเกินจำนวนที่สั่งไหม (Error Prevention: สแกนเกิน)
            if item['packed_qty'] >= item['required_qty']:
                return {"status": "error", "error_type": "over_pack", "message": f"ตี๊ดดด! สินค้านี้แพ็คครบแล้ว ห้ามใส่เกิน!"}
                
            # 4. อัปเดตยอดการแพ็ค
            cursor.execute("UPDATE fulfillment_items SET packed_qty = packed_qty + 1 WHERE id = %s", (item['id'],))
            
            # 5. ตรวจสอบว่าแพ็ค "ครบทุกชิ้น" ในออเดอร์หรือยัง
            cursor.execute("SELECT required_qty, packed_qty FROM fulfillment_items WHERE order_id = %s", (order_id,))
            all_items = cursor.fetchall()
            
            is_completed = all(i['packed_qty'] == i['required_qty'] for i in all_items)
            
            trigger_print = False
            if is_completed:
                # ปิดกล่อง อัปเดตสถานะ และส่งสัญญาณให้ Frontend สั่ง Print Label
                cursor.execute("""
                    UPDATE fulfillment_orders 
                    SET status = 'packed', packer_id = %s, packed_at = %s 
                    WHERE id = %s
                """, (scan.packer_id, datetime.now(), order_id))
                trigger_print = True
                
        conn.commit()
        
        return {
            "status": "success",
            "sku": scan.sku,
            "message": "สแกนสินค้าลงกล่องสำเร็จ",
            "order_completed": is_completed,
            "trigger_print_label": trigger_print, # Frontend จับค่านี้ไปสั่งเครื่องปริ้นเตอร์ความร้อนทำงานทันที!
            "label_data_url": f"/api/hardware/print/label/{scan.tracking_no}" if trigger_print else None
        }
    finally:
        conn.close()
