from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
from datetime import datetime

router = APIRouter()

class DocItemModel(BaseModel):
    sku: str
    product_name: str
    quantity: int
    unit_price: float
    discount_amount: float = 0.0

class CreateDocumentModel(BaseModel):
    doc_type: str # 'QT', 'INV', 'CN'
    customer_id: Optional[str] = None
    customer_name: str
    customer_tax_id: Optional[str] = None
    customer_address: Optional[str] = None
    customer_branch: str = "สำนักงานใหญ่"
    is_vat_inclusive: bool = True
    items: List[DocItemModel]

@router.post("/sales/document/create")
def create_sales_document(doc: CreateDocumentModel, tenant_id: str = Depends(verify_tenant_header)):
    """
    (2.1) ออกเอกสารงานขาย: ใบเสนอราคา (QT) หรือ ใบกำกับภาษีเต็มรูป (INV)
    ระบบจะคำนวณ VAT 7% ให้อัตโนมัติ พร้อมออกเลข Running Number
    """
    conn = get_db_connection()
    try:
        # คำนวณยอดเงิน
        subtotal = 0.0
        for item in doc.items:
            line_total = (item.quantity * item.unit_price) - item.discount_amount
            subtotal += line_total
            
        # ตรรกะคำนวณภาษี (VAT 7%)
        vat_rate = 0.07
        if doc.is_vat_inclusive:
            vat_amount = subtotal - (subtotal / (1 + vat_rate))
            net_subtotal = subtotal - vat_amount
            grand_total = subtotal
        else:
            net_subtotal = subtotal
            vat_amount = net_subtotal * vat_rate
            grand_total = net_subtotal + vat_amount

        # สร้าง Running Number ตามประเภทเอกสารและเดือน (เช่น INV-202609-0001)
        prefix = doc.doc_type.upper()
        ym_str = datetime.now().strftime("%Y%m")
        
        with conn.cursor() as cursor:
            # ดึงเลขรันนิ่งล่าสุด
            cursor.execute(f"SELECT COUNT(*) as doc_count FROM sales_documents WHERE doc_type = %s AND tenant_id = %s", (prefix, tenant_id))
            count = cursor.fetchone()['doc_count'] + 1
            doc_no = f"{prefix}-{ym_str}-{count:04d}"
            
            # บันทึกหัวเอกสาร
            cursor.execute("""
                INSERT INTO sales_documents (
                    tenant_id, doc_no, doc_type, customer_id, customer_name, 
                    customer_tax_id, customer_address, customer_branch, 
                    subtotal, vat_amount, grand_total, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'issued')
            """, (tenant_id, doc_no, prefix, doc.customer_id, doc.customer_name, 
                  doc.customer_tax_id, doc.customer_address, doc.customer_branch, 
                  net_subtotal, vat_amount, grand_total))
            
            doc_id = cursor.lastrowid
            
            # บันทึกรายการสินค้า
            for item in doc.items:
                line_total = (item.quantity * item.unit_price) - item.discount_amount
                cursor.execute("""
                    INSERT INTO sales_document_items (
                        doc_id, sku, product_name, quantity, unit_price, discount_amount, total_price
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (doc_id, item.sku, item.product_name, item.quantity, item.unit_price, item.discount_amount, line_total))
                
        conn.commit()
        return {
            "status": "success",
            "doc_no": doc_no,
            "grand_total": round(grand_total, 2),
            "vat_amount": round(vat_amount, 2),
            "message": f"ออกเอกสาร {doc_no} สำเร็จ พร้อมสำหรับการพิมพ์หรือส่ง e-Tax"
        }
    finally:
        conn.close()
