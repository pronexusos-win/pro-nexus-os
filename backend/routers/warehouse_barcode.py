from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

class WarehouseSKUItem(BaseModel):
    sku: str
    product_name: str
    warehouse_zone: str  # เช่น โซน A, โซนตู้เย็น, ชั้นวาง 3
    stock_quantity: int

@router.post("/warehouse/register-sku")
def register_sku_barcode(item: WarehouseSKUItem, tenant_id: str = Depends(verify_tenant_header)):
    """ลงทะเบียนรหัส SKU และผูกกับตำแหน่งในคลังสินค้า พร้อมสร้างข้อมูลบาร์โค้ดคลัง"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # บันทึกหรืออัปเดต SKU และตำแหน่งในคลัง
            cursor.execute("""
                INSERT INTO warehouse_inventory (tenant_id, sku, product_name, warehouse_zone, stock_quantity)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                product_name = %s, warehouse_zone = %s, stock_quantity = %s
            """, (tenant_id, item.sku, item.product_name, item.warehouse_zone, item.stock_quantity,
                  item.product_name, item.warehouse_zone, item.stock_quantity))
        conn.commit()
        
        # สร้างโครงสร้างสติกเกอร์บาร์โค้ดสำหรับแปะชั้นวางคลังสินค้าหรือตัวสินค้า
        barcode_html = f"""
        <div style="width: 250px; padding: 10px; border: 2px solid #000; font-family: sans-serif; text-align: center; background: #fff;">
            <p style="margin: 0; font-size: 11px; color: #555;">ZONE: {item.warehouse_zone}</p>
            <h3 style="margin: 5px 0; font-size: 13px;">{item.product_name}</h3>
            <p style="margin: 0; font-size: 14px; font-weight: bold;">SKU: {item.sku}</p>
            <svg class="warehouse-barcode"
              jsbarcode-value="{item.sku}"
              jsbarcode-format="CODE128"
              jsbarcode-width="1.5"
              jsbarcode-height="45"
              jsbarcode-fontsize="12">
            </svg>
            <p style="margin: 2px 0; font-size: 11px;">Stock: {item.stock_quantity} ชิ้น</p>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
        <script>JsBarcode(".warehouse-barcode").init();</script>
        """
        
        return {
            "status": "success",
            "sku": item.sku,
            "warehouse_zone": item.warehouse_zone,
            "print_layout": barcode_html,
            "message": f"ลงทะเบียน SKU '{item.sku}' และสร้างบาร์โค้ดคลังสำเร็จ!"
        }
    finally:
        conn.close()

@router.get("/warehouse/scan/{sku}")
def scan_warehouse_sku(sku: str, tenant_id: str = Depends(verify_tenant_header)):
    """สแกนบาร์โค้ด SKU เพื่อเช็กสต็อกและตำแหน่งในคลังหลังร้านทันที"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT sku, product_name, warehouse_zone, stock_quantity, updated_at 
                FROM warehouse_inventory 
                WHERE tenant_id = %s AND sku = %s
            """, (tenant_id, sku))
            item = cursor.fetchone()
            
            if not item:
                raise HTTPException(status_code=404, detail="ไม่พบสินค้ารหัส SKU นี้ในระบบคลัง")
                
        return {
            "status": "success",
            "warehouse_info": item
        }
    finally:
        conn.close()
