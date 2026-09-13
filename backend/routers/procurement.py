from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
import uuid

router = APIRouter()

class POItemModel(BaseModel):
    sku: str
    order_qty: int
    unit_price: float

class CreatePOModel(BaseModel):
    supplier_id: int
    items: List[POItemModel]

class ReceiveItemModel(BaseModel):
    sku: str
    receive_qty: int

class GoodsReceiptModel(BaseModel):
    po_id: int
    receiver_id: str
    items: List[ReceiveItemModel]

@router.post("/procurement/po")
def create_purchase_order(po: CreatePOModel, tenant_id: str = Depends(verify_tenant_header)):
    """สร้างใบสั่งซื้อ (PO) สถานะ 0 (รออนุมัติ) หรือ 1 (สั่งแล้ว)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            po_number = f"PO-{uuid.uuid4().hex[:8].upper()}"
            total_amount = sum([item.order_qty * item.unit_price for item in po.items])
            
            cursor.execute("""
                INSERT INTO purchase_orders (tenant_id, po_number, supplier_id, status, total_amount)
                VALUES (%s, %s, %s, 1, %s)
            """, (tenant_id, po_number, po.supplier_id, total_amount))
            po_id = cursor.lastrowid
            
            for item in po.items:
                cursor.execute("""
                    INSERT INTO po_items (po_id, sku, order_qty, unit_price)
                    VALUES (%s, %s, %s, %s)
                """, (po_id, item.sku, item.order_qty, item.unit_price))
                
        conn.commit()
        return {"status": "success", "po_number": po_number, "message": "เปิดใบสั่งซื้อ (PO) สำเร็จ สถานะ 1 (สั่งแล้ว)"}
    finally:
        conn.close()

@router.post("/procurement/gr")
def create_goods_receipt(gr: GoodsReceiptModel, tenant_id: str = Depends(verify_tenant_header)):
    """ทำใบรับสินค้า (GR) อัปเดตสถานะ PO และเอาของเข้าคลังอัตโนมัติ"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. เช็กหัวบิล PO
            cursor.execute("SELECT status FROM purchase_orders WHERE id = %s AND tenant_id = %s", (gr.po_id, tenant_id))
            po_record = cursor.fetchone()
            if not po_record or po_record['status'] == 9:
                raise HTTPException(status_code=400, detail="PO นี้รับครบแล้ว หรือไม่พบข้อมูล")

            gr_number = f"GR-{uuid.uuid4().hex[:8].upper()}"
            cursor.execute("INSERT INTO goods_receipts (tenant_id, gr_number, po_id, receiver_id) VALUES (%s, %s, %s, %s)", 
                           (tenant_id, gr_number, gr.po_id, gr.receiver_id))
            
            all_completed = True
            
            # 2. วนลูปรับของและอัปเดตยอด
            for r_item in gr.items:
                # อัปเดตยอดรับใน PO item
                cursor.execute("""
                    UPDATE po_items SET received_qty = received_qty + %s 
                    WHERE po_id = %s AND sku = %s
                """, (r_item.receive_qty, gr.po_id, r_item.sku))
                
                # เช็กว่ายอดที่รับมาครบตามที่สั่งหรือยัง
                cursor.execute("SELECT order_qty, received_qty FROM po_items WHERE po_id = %s AND sku = %s", (gr.po_id, r_item.sku))
                check_qty = cursor.fetchone()
                if check_qty['received_qty'] < check_qty['order_qty']:
                    all_completed = False
                
                # 3. เอาของเข้าคลังหลัก (ซิงค์ WMS)
                cursor.execute("""
                    UPDATE warehouse_inventory SET stock_quantity = stock_quantity + %s 
                    WHERE tenant_id = %s AND sku = %s
                """, (r_item.receive_qty, tenant_id, r_item.sku))

            # 4. อัปเดตสถานะ PO (9 = ครบ, 2 = ขาด)
            new_status = 9 if all_completed else 2
            cursor.execute("UPDATE purchase_orders SET status = %s WHERE id = %s", (new_status, gr.po_id))
            
        conn.commit()
        return {
            "status": "success", 
            "gr_number": gr_number,
            "po_status_updated_to": new_status,
            "message": "รับของเข้าคลังสำเร็จ และอัปเดตสถานะ PO แล้ว"
        }
    finally:
        conn.close()
