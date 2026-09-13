from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

class BOMComponent(BaseModel):
    component_sku: str
    quantity: float
    unit: str = "ชิ้น"

class CreateBOMRequest(BaseModel):
    parent_sku: str
    components: List[BOMComponent]

@router.post("/inventory/bom")
def create_bom_recipe(recipe: CreateBOMRequest, tenant_id: str = Depends(verify_tenant_header)):
    """ผูกสูตรส่วนผสม (BOM) หรือจัดชุดสินค้า ให้กับ SKU หลัก"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ลบสูตรเดิมก่อน (ถ้ามี) เพื่ออัปเดตใหม่
            cursor.execute("DELETE FROM product_bom WHERE tenant_id = %s AND parent_sku = %s", (tenant_id, recipe.parent_sku))
            
            # บันทึกสูตรใหม่
            for comp in recipe.components:
                cursor.execute("""
                    INSERT INTO product_bom (tenant_id, parent_sku, component_sku, quantity, unit)
                    VALUES (%s, %s, %s, %s, %s)
                """, (tenant_id, recipe.parent_sku, comp.component_sku, comp.quantity, comp.unit))
        conn.commit()
        return {"status": "success", "message": f"บันทึกสูตร BOM สำหรับ {recipe.parent_sku} สำเร็จ"}
    finally:
        conn.close()

@router.get("/inventory/bom/{sku}")
def get_bom_recipe(sku: str, tenant_id: str = Depends(verify_tenant_header)):
    """ดูส่วนผสมของสินค้าชุด/เมนูอาหาร"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT b.component_sku, p.product_name, b.quantity, b.unit 
                FROM product_bom b
                LEFT JOIN products p ON b.component_sku = p.sku AND b.tenant_id = p.tenant_id
                WHERE b.tenant_id = %s AND b.parent_sku = %s
            """, (tenant_id, sku))
            components = cursor.fetchall()
            
        return {"status": "success", "parent_sku": sku, "components": components}
    finally:
        conn.close()

@router.post("/inventory/bom/deduct")
def deduct_bom_stock(parent_sku: str, sell_qty: int = 1, tenant_id: str = Depends(verify_tenant_header)):
    """
    (จำลอง) ระบบตัดสต็อกอัตโนมัติเมื่อขายสินค้าชุด
    API นี้จะถูกเรียกใช้เป็นฟังก์ชันหลังบ้านเวลามีการ Checkout ในโหมดขายจริง
    """
    conn = get_db_connection()
    try:
        deducted_items = []
        with conn.cursor() as cursor:
            # 1. ดึงสูตร BOM 
            cursor.execute("SELECT component_sku, quantity FROM product_bom WHERE tenant_id = %s AND parent_sku = %s", (tenant_id, parent_sku))
            components = cursor.fetchall()
            
            if not components:
                return {"status": "info", "message": "ไม่พบสูตร BOM (เป็นสินค้าชิ้นเดี่ยว)"}
                
            # 2. วนลูปตัดสต็อกวัตถุดิบ (WMS)
            for comp in components:
                total_deduct = float(comp['quantity']) * sell_qty
                
                cursor.execute("""
                    UPDATE warehouse_inventory 
                    SET stock_quantity = stock_quantity - %s 
                    WHERE tenant_id = %s AND sku = %s
                """, (total_deduct, tenant_id, comp['component_sku']))
                
                deducted_items.append({"sku": comp['component_sku'], "deducted": total_deduct})
                
        conn.commit()
        return {
            "status": "success", 
            "message": f"ขาย {parent_sku} จำนวน {sell_qty} ชุด -> ตัดสต็อกวัตถุดิบสำเร็จ",
            "deducted_materials": deducted_items
        }
    finally:
        conn.close()
