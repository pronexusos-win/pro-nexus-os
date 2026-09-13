from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
from datetime import datetime

router = APIRouter()

class OfflineItemModel(BaseModel):
    sku: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

class OfflineOrderModel(BaseModel):
    offline_tx_id: str
    doc_type: str = "INV"
    subtotal: float
    vat_amount: float
    grand_total: float
    items: List[OfflineItemModel]
    timestamp: str # เวลาตอนที่กดขายแบบออฟไลน์

class SyncBatchModel(BaseModel):
    orders: List[OfflineOrderModel]

@router.post("/sales/sync-offline")
def sync_offline_orders(batch: SyncBatchModel, tenant_id: str = Depends(verify_tenant_header)):
    """
    (2.4) รับบิลที่ค้างในเครื่องตอนเน็ตหลุด สาดขึ้นคลาวด์
    ระบบจะข้ามบิลที่ offline_tx_id ซ้ำ (เคยซิงค์แล้ว) เพื่อป้องกันสต็อกพัง
    """
    conn = get_db_connection()
    try:
        synced_count = 0
        skipped_count = 0
        
        with conn.cursor() as cursor:
            for order in batch.orders:
                # 1. เช็กว่าบิลนี้เคยซิงค์หรือยัง
                cursor.execute("SELECT id FROM sales_documents WHERE offline_tx_id = %s", (order.offline_tx_id,))
                if cursor.fetchone():
                    skipped_count += 1
                    continue # ข้ามบิลนี้
                    
                # 2. สร้างเลขบิลรันนิ่งใหม่ของระบบคลาวด์
                ym_str = datetime.now().strftime("%Y%m")
                cursor.execute(f"SELECT COUNT(*) as doc_count FROM sales_documents WHERE doc_type = %s AND tenant_id = %s", (order.doc_type, tenant_id))
                count = cursor.fetchone()['doc_count'] + 1
                doc_no = f"{order.doc_type}-{ym_str}-{count:04d}-SYNC"
                
                # 3. บันทึกหัวบิล
                cursor.execute("""
                    INSERT INTO sales_documents (
                        tenant_id, doc_no, doc_type, subtotal, vat_amount, grand_total, status, offline_tx_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'issued', %s)
                """, (tenant_id, doc_no, order.doc_type, order.subtotal, order.vat_amount, order.grand_total, order.offline_tx_id))
                doc_id = cursor.lastrowid
                
                # 4. บันทึกรายการสินค้าและตัดสต็อกส่วนกลาง
                for item in order.items:
                    cursor.execute("""
                        INSERT INTO sales_document_items (doc_id, sku, product_name, quantity, unit_price, total_price) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (doc_id, item.sku, item.product_name, item.quantity, item.unit_price, item.total_price))
                    
                    # หักสต็อก WMS (หากสต็อกติดลบ ระบบจะยอมให้ติดลบไปก่อน เพราะขายไปแล้วตอนออฟไลน์)
                    cursor.execute("""
                        UPDATE warehouse_inventory SET stock_quantity = stock_quantity - %s 
                        WHERE tenant_id = %s AND sku = %s
                    """, (item.quantity, tenant_id, item.sku))
                    
                synced_count += 1
                
        conn.commit()
        return {
            "status": "success",
            "summary": f"รับข้อมูลทั้งหมด {len(batch.orders)} บิล | ซิงค์สำเร็จ {synced_count} | ข้ามบิลซ้ำ {skipped_count}"
        }
    finally:
        conn.close()
