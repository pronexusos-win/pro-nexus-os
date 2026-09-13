from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
from datetime import date

router = APIRouter()

class PaymentModel(BaseModel):
    doc_ref: str
    amount: float
    payment_date: date
    description: Optional[str] = None

@router.get("/finance/ar/pending")
def get_pending_receivables(tenant_id: str = Depends(verify_tenant_header)):
    """ดึงรายการลูกหนี้การค้าที่ยังค้างชำระ (AR)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT customer_id, doc_ref, total_amount, paid_amount, 
                       (total_amount - paid_amount) AS balance, due_date, status 
                FROM accounts_receivable 
                WHERE tenant_id = %s AND status != 'paid'
                ORDER BY due_date ASC
            """, (tenant_id,))
            return {"status": "success", "data": cursor.fetchall()}
    finally:
        conn.close()

@router.post("/finance/ar/receive")
def receive_ar_payment(payment: PaymentModel, tenant_id: str = Depends(verify_tenant_header)):
    """(4.2 & 4.1) รับชำระเงินจากลูกหนี้ -> ตัดยอด AR -> บันทึกสมุดรายวัน (IN)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT total_amount, paid_amount FROM accounts_receivable WHERE tenant_id = %s AND doc_ref = %s", (tenant_id, payment.doc_ref))
            ar = cursor.fetchone()
            if not ar:
                raise HTTPException(status_code=404, detail="ไม่พบเอกสารลูกหนี้")
                
            new_paid = float(ar['paid_amount']) + payment.amount
            status = 'paid' if new_paid >= float(ar['total_amount']) else 'partial'
            
            # 1. อัปเดตลูกหนี้
            cursor.execute("UPDATE accounts_receivable SET paid_amount = %s, status = %s WHERE tenant_id = %s AND doc_ref = %s", 
                           (new_paid, status, tenant_id, payment.doc_ref))
                           
            # 2. บันทึกรายรับลงสมุดรายวัน
            cursor.execute("""
                INSERT INTO cash_book (tenant_id, trans_date, trans_type, category, amount, description, ref_doc)
                VALUES (%s, %s, 'IN', 'AR_RECEIPT', %s, %s, %s)
            """, (tenant_id, payment.payment_date, payment.amount, payment.description or "รับชำระหนี้จากลูกค้า", payment.doc_ref))
            
        conn.commit()
        return {"status": "success", "message": f"ตัดยอดรับชำระ {payment.amount} บาทสำเร็จ (สถานะ: {status})"}
    finally:
        conn.close()

@router.post("/finance/ap/pay")
def pay_ap_supplier(payment: PaymentModel, tenant_id: str = Depends(verify_tenant_header)):
    """(4.2 & 4.1) จ่ายเงินให้ซัพพลายเออร์ -> ตัดยอด AP -> บันทึกสมุดรายวัน (OUT)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT total_amount, paid_amount FROM accounts_payable WHERE tenant_id = %s AND doc_ref = %s", (tenant_id, payment.doc_ref))
            ap = cursor.fetchone()
            if not ap:
                raise HTTPException(status_code=404, detail="ไม่พบเอกสารเจ้าหนี้")
                
            new_paid = float(ap['paid_amount']) + payment.amount
            status = 'paid' if new_paid >= float(ap['total_amount']) else 'partial'
            
            # 1. อัปเดตเจ้าหนี้
            cursor.execute("UPDATE accounts_payable SET paid_amount = %s, status = %s WHERE tenant_id = %s AND doc_ref = %s", 
                           (new_paid, status, tenant_id, payment.doc_ref))
                           
            # 2. บันทึกรายจ่ายลงสมุดรายวัน
            cursor.execute("""
                INSERT INTO cash_book (tenant_id, trans_date, trans_type, category, amount, description, ref_doc)
                VALUES (%s, %s, 'OUT', 'AP_PAYMENT', %s, %s, %s)
            """, (tenant_id, payment.payment_date, payment.amount, payment.description or "จ่ายชำระหนี้ซัพพลายเออร์", payment.doc_ref))
            
        conn.commit()
        return {"status": "success", "message": f"บันทึกจ่ายเงิน {payment.amount} บาทสำเร็จ (สถานะ: {status})"}
    finally:
        conn.close()

@router.get("/finance/cash-book")
def get_cash_book(target_date: date = None, tenant_id: str = Depends(verify_tenant_header)):
    """(4.1) ดูรายงานสมุดรายวันรับ-จ่าย ประจำวัน"""
    conn = get_db_connection()
    try:
        t_date = target_date or date.today()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT trans_type, category, amount, description, ref_doc 
                FROM cash_book WHERE tenant_id = %s AND trans_date = %s
                ORDER BY created_at DESC
            """, (tenant_id, t_date))
            records = cursor.fetchall()
            
            total_in = sum(float(r['amount']) for r in records if r['trans_type'] == 'IN')
            total_out = sum(float(r['amount']) for r in records if r['trans_type'] == 'OUT')
            
            return {
                "status": "success", 
                "date": t_date,
                "summary": {"total_in": total_in, "total_out": total_out, "net_cash": total_in - total_out},
                "records": records
            }
    finally:
        conn.close()
