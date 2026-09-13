from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
from datetime import datetime
import uuid

router = APIRouter()

class ExpenseModel(BaseModel):
    description: str
    subtotal: float
    has_vat: bool = False  # มี VAT 7% ไหม
    wht_rate: float = 0.0  # อัตราหัก ณ ที่จ่าย (เช่น 0.03 สำหรับ 3%)
    payee_name: Optional[str] = None
    payee_tax_id: Optional[str] = None

def auto_categorize(description: str) -> str:
    """ระบบ Rule-based AI อย่างง่าย สำหรับแยกหมวดหมู่รายจ่ายอัตโนมัติ"""
    desc = description.lower()
    if any(keyword in desc for keyword in ["ค่าไฟ", "ค่าน้ำ", "ค่าเน็ต", "โทรศัพท์"]):
        return "UTILITIES" # ค่าสาธารณูปโภค
    elif any(keyword in desc for keyword in ["คอมมิชชัน", "affiliate", "นายหน้า", "gp"]):
        return "COMMISSION" # ค่าคอมมิชชัน
    elif any(keyword in desc for keyword in ["เงินเดือน", "ค่าจ้าง", "ot"]):
        return "PAYROLL" # เงินเดือนพนักงาน
    elif any(keyword in desc for keyword in ["ซ่อม", "อะไหล่", "บำรุง"]):
        return "MAINTENANCE" # ค่าซ่อมบำรุง
    elif any(keyword in desc for keyword in ["โฆษณา", "การตลาด", "ยิงแอด"]):
        return "MARKETING" # ค่าการตลาด
    return "MISCELLANEOUS" # จิปาถะอื่นๆ

@router.post("/finance/expense/record")
def record_smart_expense(expense: ExpenseModel, tenant_id: str = Depends(verify_tenant_header)):
    """(4.3) บันทึกรายจ่าย แยกหมวดหมู่อัตโนมัติ พร้อมหักภาษี 3% และ VAT 7%"""
    conn = get_db_connection()
    try:
        # 1. วิเคราะห์หมวดหมู่อัตโนมัติ
        category = auto_categorize(expense.description)
        
        # 2. คำนวณภาษี
        vat_amount = expense.subtotal * 0.07 if expense.has_vat else 0.0
        wht_amount = expense.subtotal * expense.wht_rate # หัก ณ ที่จ่ายคำนวณจากยอดก่อน VAT เสมอ
        
        # ยอดสุทธิที่ต้องโอน/จ่ายเงินสด (Base + VAT - หัก ณ ที่จ่าย)
        net_paid = expense.subtotal + vat_amount - wht_amount
        
        doc_no = f"EXP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        
        with conn.cursor() as cursor:
            # 3. บันทึกลงตารางรายจ่ายและภาษี
            cursor.execute("""
                INSERT INTO expense_transactions (
                    tenant_id, doc_no, category, description, subtotal, 
                    vat_amount, wht_amount, net_paid, payee_name, payee_tax_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (tenant_id, doc_no, category, expense.description, expense.subtotal, 
                  vat_amount, wht_amount, net_paid, expense.payee_name, expense.payee_tax_id))
            
            # 4. ซิงค์ยอดเงินออกไปที่ตารางสมุดรายวัน (Cash Book) ทันที
            cursor.execute("""
                INSERT INTO cash_book (tenant_id, trans_date, trans_type, category, amount, description, ref_doc)
                VALUES (%s, CURRENT_DATE(), 'OUT', %s, %s, %s, %s)
            """, (tenant_id, category, net_paid, f"{expense.description} (หักภาษีแล้ว)", doc_no))
            
        conn.commit()
        return {
            "status": "success",
            "doc_no": doc_no,
            "category_assigned": category,
            "financial_summary": {
                "base_amount": round(expense.subtotal, 2),
                "vat_7_percent": round(vat_amount, 2),
                "wht_deducted": round(wht_amount, 2),
                "actual_paid_amount": round(net_paid, 2)
            },
            "message": "บันทึกรายจ่ายและหักภาษีสำเร็จ พร้อมส่งข้อมูลลงสมุดรายวัน"
        }
    finally:
        conn.close()
