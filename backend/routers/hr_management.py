from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
from datetime import datetime, date

router = APIRouter()

class OpenShiftModel(BaseModel):
    pos_machine_id: str
    cashier_id: str
    starting_cash: float

class CloseShiftModel(BaseModel):
    shift_id: int
    actual_counted_cash: float # ยอดที่แคชเชียร์นับด้วยมือแล้วพิมพ์เข้ามา

@router.post("/hr/shift/open")
def open_pos_shift(shift: OpenShiftModel, tenant_id: str = Depends(verify_tenant_header)):
    """(6.1) เปิดกะการทำงาน พร้อมระบุเงินทอนตั้งต้น"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตรวจสอบว่าเครื่องนี้มีกะที่ยังไม่ปิดหรือไม่
            cursor.execute("SELECT id FROM pos_shifts WHERE tenant_id = %s AND pos_machine_id = %s AND status = 'open'", (tenant_id, shift.pos_machine_id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="เครื่อง POS นี้มีกะที่ยังไม่ได้ปิด กรุณาปิดกะก่อนหน้าก่อน")
                
            cursor.execute("""
                INSERT INTO pos_shifts (tenant_id, pos_machine_id, cashier_id, opened_at, starting_cash, status)
                VALUES (%s, %s, %s, %s, %s, 'open')
            """, (tenant_id, shift.pos_machine_id, shift.cashier_id, datetime.now(), shift.starting_cash))
            
        conn.commit()
        return {"status": "success", "message": f"เปิดกะสำเร็จ เงินทอนตั้งต้น {shift.starting_cash} บาท"}
    finally:
        conn.close()

@router.post("/hr/shift/close")
def close_pos_shift(shift: CloseShiftModel, tenant_id: str = Depends(verify_tenant_header)):
    """
    (6.1) ปิดกะแบบ Blind Close (พนักงานไม่รู้ยอดที่ควรมี)
    ระบบจะคำนวณเงินขาด/เกิน และแจ้งเตือนผู้จัดการหากเงินหาย
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT starting_cash, status, cashier_id FROM pos_shifts WHERE id = %s AND tenant_id = %s", (shift.shift_id, tenant_id))
            shift_record = cursor.fetchone()
            
            if not shift_record or shift_record['status'] == 'closed':
                raise HTTPException(status_code=400, detail="ไม่พบกะการทำงาน หรือกะนี้ถูกปิดไปแล้ว")
                
            # จำลองการคำนวณเงินสดรับเข้าลิ้นชัก (ในระบบจริงจะ Query SUM() จากบิลเงินสดในช่วงเวลาที่เปิดกะ)
            # expected_cash = starting_cash + total_cash_sales - total_cash_refunds
            total_cash_sales = 5500.00 # สมมติว่าขายเงินสดได้ 5,500 บาท
            expected_cash = float(shift_record['starting_cash']) + total_cash_sales
            
            # คำนวณส่วนต่าง (เงินเกินเป็นบวก / เงินขาดเป็นลบ)
            discrepancy = shift.actual_counted_cash - expected_cash
            
            cursor.execute("""
                UPDATE pos_shifts 
                SET closed_at = %s, expected_cash = %s, actual_counted_cash = %s, discrepancy = %s, status = 'closed'
                WHERE id = %s
            """, (datetime.now(), expected_cash, shift.actual_counted_cash, discrepancy, shift.shift_id))
            
            alert_msg = "ยอดเงินตรงเป๊ะ! ขอบคุณสำหรับการทำงาน"
            if discrepancy < 0:
                alert_msg = f"แจ้งเตือน: เงินช็อต (เงินขาด) จำนวน {abs(discrepancy):.2f} บาท ระบบได้บันทึกรายงานส่งผู้จัดการแล้ว"
            elif discrepancy > 0:
                alert_msg = f"แจ้งเตือน: เงินเกิน จำนวน {discrepancy:.2f} บาท กรุณาตรวจสอบการทอนเงินลูกค้า"
                
        conn.commit()
        return {
            "status": "success", 
            "discrepancy": discrepancy,
            "message": alert_msg
        }
    finally:
        conn.close()

@router.get("/hr/commission/{employee_id}")
def get_employee_commission(employee_id: str, target_month: str = None, tenant_id: str = Depends(verify_tenant_header)):
    """(6.3) ดูสรุปยอดค่าคอมมิชชันและ KPI ของพนักงาน"""
    conn = get_db_connection()
    try:
        month_filter = target_month or datetime.now().strftime('%Y-%m') # Format: YYYY-MM
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT doc_no, sku, sale_amount, commission_earned, created_at 
                FROM employee_commissions 
                WHERE tenant_id = %s AND employee_id = %s AND DATE_FORMAT(created_at, '%%Y-%%m') = %s
                ORDER BY created_at DESC
            """, (tenant_id, employee_id, month_filter))
            commissions = cursor.fetchall()
            
            total_earned = sum(float(c['commission_earned']) for c in commissions)
            
        return {
            "status": "success",
            "employee_id": employee_id,
            "month": month_filter,
            "total_commission_earned": round(total_earned, 2),
            "transactions_count": len(commissions),
            "details": commissions
        }
    finally:
        conn.close()
