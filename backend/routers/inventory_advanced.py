from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
from datetime import date

router = APIRouter()

class ReceiveLotModel(BaseModel):
    sku: str
    lot_number: str
    cost_price: float
    quantity: int
    mfg_date: Optional[date] = None
    exp_date: Optional[date] = None

@router.post("/inventory/receive-lot")
def receive_inventory_lot(lot: ReceiveLotModel, tenant_id: str = Depends(verify_tenant_header)):
    """
    รับสินค้าเข้าคลังแบบระบุ Lot พร้อมคำนวณต้นทุนเฉลี่ย (Moving Average Cost)
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. บันทึกข้อมูลเข้าตาราง Lot
            cursor.execute("""
                INSERT INTO inventory_lots (tenant_id, sku, lot_number, cost_price, quantity, mfg_date, exp_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                quantity = quantity + %s, cost_price = %s
            """, (tenant_id, lot.sku, lot.lot_number, lot.cost_price, lot.quantity, lot.mfg_date, lot.exp_date, lot.quantity, lot.cost_price))
            
            # 2. ดึงข้อมูลสต็อกและต้นทุนเดิม เพื่อคำนวณ Moving Average
            cursor.execute("SELECT moving_avg_cost FROM products WHERE tenant_id = %s AND sku = %s", (tenant_id, lot.sku))
            product = cursor.fetchone()
            
            cursor.execute("SELECT stock_quantity FROM warehouse_inventory WHERE tenant_id = %s AND sku = %s", (tenant_id, lot.sku))
            inv = cursor.fetchone()
            
            old_cost = float(product['moving_avg_cost']) if product and product['moving_avg_cost'] else 0.0
            old_qty = float(inv['stock_quantity']) if inv and inv['stock_quantity'] else 0.0
            
            # สูตร Moving Average Cost = [(Old Qty * Old Cost) + (New Qty * New Cost)] / (Old Qty + New Qty)
            new_total_qty = old_qty + lot.quantity
            if new_total_qty > 0:
                new_mac = ((old_qty * old_cost) + (lot.quantity * lot.cost_price)) / new_total_qty
            else:
                new_mac = lot.cost_price
                
            # 3. อัปเดต MAC ในตารางสินค้า และเพิ่มสต็อกรวม
            cursor.execute("UPDATE products SET moving_avg_cost = %s WHERE tenant_id = %s AND sku = %s", (new_mac, tenant_id, lot.sku))
            cursor.execute("""
                UPDATE warehouse_inventory SET stock_quantity = stock_quantity + %s 
                WHERE tenant_id = %s AND sku = %s
            """, (lot.quantity, tenant_id, lot.sku))
            
        conn.commit()
        return {
            "status": "success",
            "message": f"รับล็อต {lot.lot_number} เข้าคลังเรียบร้อย ต้นทุนเฉลี่ยใหม่ (MAC) คือ ฿{new_mac:.4f}"
        }
    finally:
        conn.close()

@router.get("/inventory/fefo-picking/{sku}")
def get_fefo_picking_list(sku: str, required_qty: int, tenant_id: str = Depends(verify_tenant_header)):
    """
    ระบบแนะนำการหยิบสินค้าแบบ FEFO (First-Expire-First-Out)
    เพื่อให้พนักงานจัดของรู้ว่าควรหยิบจาก Lot ไหนก่อน
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # เรียงจากวันหมดอายุใกล้สุดไปไกลสุด
            cursor.execute("""
                SELECT lot_number, quantity, exp_date 
                FROM inventory_lots 
                WHERE tenant_id = %s AND sku = %s AND quantity > 0
                ORDER BY exp_date ASC, created_at ASC
            """, (tenant_id, sku))
            lots = cursor.fetchall()
            
            picking_plan = []
            qty_needed = required_qty
            
            for l in lots:
                if qty_needed <= 0:
                    break
                take_qty = min(l['quantity'], qty_needed)
                picking_plan.append({
                    "lot_number": l['lot_number'],
                    "exp_date": l['exp_date'],
                    "pick_quantity": take_qty
                })
                qty_needed -= take_qty
                
        return {"status": "success", "required_qty": required_qty, "picking_plan": picking_plan}
    finally:
        conn.close()

@router.get("/inventory/alerts/expiring")
def get_expiring_alerts(days_ahead: int = 30, tenant_id: str = Depends(verify_tenant_header)):
    """แจ้งเตือนสินค้าใกล้หมดอายุภายใน X วัน (Smart Alerts)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT sku, lot_number, quantity, exp_date 
                FROM inventory_lots 
                WHERE tenant_id = %s AND quantity > 0 
                  AND exp_date IS NOT NULL 
                  AND exp_date <= DATE_ADD(CURRENT_DATE(), INTERVAL %s DAY)
                ORDER BY exp_date ASC
            """, (tenant_id, days_ahead))
            alerts = cursor.fetchall()
            
        return {"status": "success", "alert_count": len(alerts), "expiring_items": alerts}
    finally:
        conn.close()
