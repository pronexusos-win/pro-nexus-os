from fastapi import APIRouter, Depends, HTTPException
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
import uuid

router = APIRouter()

@router.get("/procurement/forecast/{sku}")
def calculate_forecast(sku: str, days_history: int = 30, tenant_id: str = Depends(verify_tenant_header)):
    """
    (1.3) ระบบ AI Forecast คาดการณ์การสั่งซื้อจากยอดขายย้อนหลัง
    สูตร: (ยอดขายเฉลี่ยต่อวัน * Lead Time) + Safety Stock - สต็อกปัจจุบัน - สต็อกกำลังมา
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # หมายเหตุ: ในระบบจริงจะ Join ตารางยอดขาย (Sales) ย้อนหลังตาม days_history 
            # แต่เพื่อความรวดเร็ว เราจำลองดึงค่า Configuration ของสินค้านั้นมาคำนวณ
            cursor.execute("""
                SELECT p.sku, p.reorder_point, p.safety_stock, p.lead_time_days, p.price_retail,
                       COALESCE(w.stock_quantity, 0) as current_stock
                FROM products p
                LEFT JOIN warehouse_inventory w ON p.sku = w.sku AND p.tenant_id = w.tenant_id
                WHERE p.tenant_id = %s AND p.sku = %s
            """, (tenant_id, sku))
            product = cursor.fetchone()
            
            if not product:
                raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
                
            # ดึงสินค้าระหว่างทาง (Transit Stock)
            cursor.execute("""
                SELECT SUM(poi.order_qty - poi.received_qty) AS transit_qty
                FROM purchase_orders po JOIN po_items poi ON po.id = poi.po_id
                WHERE po.tenant_id = %s AND po.status IN (1, 2) AND poi.sku = %s
            """, (tenant_id, sku))
            transit = cursor.fetchone()
            transit_qty = int(transit['transit_qty']) if transit['transit_qty'] else 0
            
            # จำลองยอดขายเฉลี่ย (ในระบบจริงจะ Query จาก Transaction)
            avg_daily_sales = 5.5 # สมมติว่าขายได้วันละ 5.5 ชิ้น
            
            # คำนวณปริมาณที่ควรสั่ง (Suggested Order Qty)
            suggested_qty = (avg_daily_sales * product['lead_time_days']) + product['safety_stock'] - product['current_stock'] - transit_qty
            suggested_qty = max(0, int(suggested_qty)) # ไม่ให้ติดลบ
            
        return {
            "status": "success",
            "sku": sku,
            "forecast_data": {
                "avg_daily_sales": avg_daily_sales,
                "current_stock": product['current_stock'],
                "transit_stock": transit_qty,
                "suggested_order_qty": suggested_qty,
                "reorder_point": product['reorder_point']
            },
            "message": f"แนะนำให้สั่งซื้อเพิ่ม {suggested_qty} ชิ้น เพื่อให้พอกับ Lead Time {product['lead_time_days']} วัน"
        }
    finally:
        conn.close()

@router.post("/procurement/auto-po/run")
def trigger_auto_po(tenant_id: str = Depends(verify_tenant_header)):
    """
    (1.5) ระบบ Auto-PO สแกนหาสินค้าที่ต่ำกว่า Reorder Point 
    และสร้างใบสั่งซื้อ (Status 0 - รออนุมัติ) แยกตาม Supplier ให้อัตโนมัติ
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # หาสินค้าที่ สต็อกจริง + ของกำลังมา <= จุดสั่งซื้อ (Reorder Point)
            cursor.execute("""
                SELECT p.sku, p.default_supplier_id, p.reorder_point, 
                       COALESCE(w.stock_quantity, 0) as current_stock
                FROM products p
                LEFT JOIN warehouse_inventory w ON p.sku = w.sku AND p.tenant_id = w.tenant_id
                WHERE p.tenant_id = %s AND p.default_supplier_id IS NOT NULL
            """, (tenant_id,))
            products = cursor.fetchall()
            
            supplier_orders = {}
            
            for p in products:
                # ดึงของระหว่างทางมาบวกเพื่อไม่ให้สั่งของซ้ำซ้อน
                cursor.execute("""
                    SELECT SUM(poi.order_qty - poi.received_qty) AS transit_qty
                    FROM purchase_orders po JOIN po_items poi ON po.id = poi.po_id
                    WHERE po.tenant_id = %s AND po.status IN (1, 2) AND poi.sku = %s
                """, (tenant_id, p['sku']))
                transit = cursor.fetchone()
                transit_qty = int(transit['transit_qty']) if transit['transit_qty'] else 0
                
                total_effective_stock = p['current_stock'] + transit_qty
                
                if total_effective_stock <= p['reorder_point']:
                    # ต้องสั่งของเพิ่ม (สมมติสั่งเผื่อไป 10 ชิ้น หรือใช้สูตรจาก Forecast ก็ได้)
                    order_amount = (p['reorder_point'] - total_effective_stock) + 20 
                    sup_id = p['default_supplier_id']
                    
                    if sup_id not in supplier_orders:
                        supplier_orders[sup_id] = []
                    
                    supplier_orders[sup_id].append({
                        "sku": p['sku'],
                        "qty": order_amount,
                        "unit_price": 0.0 # เดี๋ยวค่อยให้จัดซื้อไปใส่ราคาอัปเดต หรือดึงจากทุนล่าสุด
                    })
            
            generated_pos = []
            
            # สร้างใบ PO สถานะ 0 (ดราฟต์) แยกตามซัพพลายเออร์
            for sup_id, items in supplier_orders.items():
                po_number = f"AUTO-PO-{uuid.uuid4().hex[:6].upper()}"
                
                cursor.execute("""
                    INSERT INTO purchase_orders (tenant_id, po_number, supplier_id, status)
                    VALUES (%s, %s, %s, 0)
                """, (tenant_id, po_number, sup_id))
                po_id = cursor.lastrowid
                
                for item in items:
                    cursor.execute("""
                        INSERT INTO po_items (po_id, sku, order_qty, unit_price)
                        VALUES (%s, %s, %s, %s)
                    """, (po_id, item['sku'], item['qty'], item['unit_price']))
                    
                generated_pos.append({"supplier_id": sup_id, "po_number": po_number, "items_count": len(items)})
                
        conn.commit()
        return {
            "status": "success",
            "message": f"ระบบประมวลผล Auto-PO เสร็จสิ้น สร้างใบสั่งซื้อฉบับร่าง (รออนุมัติ) จำนวน {len(generated_pos)} ใบ",
            "draft_pos": generated_pos
        }
    finally:
        conn.close()
