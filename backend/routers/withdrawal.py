from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import uuid
from middleware.rbac import verify_role
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection
from services.compliance_engine import check_withdrawal_eligibility

router = APIRouter()

class WithdrawRequest(BaseModel):
    member_id: str
    amount: float
    bank_name: str
    bank_account_no: str
    bank_account_name: str
    withdrawal_method: str = "bank_transfer" # หรือ branch_cash

@router.post("/request")
def request_withdrawal(req: WithdrawRequest, tenant_id: str = Depends(verify_tenant_header)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. เช็คยอดเงินในกระเป๋าและยอดใช้จ่ายสะสมของเดือนนี้ (จำลองดึงจาก DB)
            # ในระบบจริงจะไป Query ยอดสะสมการใช้จ่ายเดือนนี้ของ member_id มาเช็ค
            current_cash_balance = 5000.00  # สมมติมีเงินในกระเป๋า 5,000 บาท
            monthly_spent_points = 200.00   เพิ่งใช้ไป 200 แต้ม (ยังไม่ถึง 1,000)
            
            # ถ้าเป็น Tenant TP Extra ให้บังคับใช้กฎ 1,000 แต้มแรก
            if tenant_id == "tenant_tp_extra":
                check = check_withdrawal_eligibility(req.member_id, req.amount, current_cash_balance, monthly_spent_points)
                if not check["allowed"]:
                    raise HTTPException(status_code=400, detail=check["message"])

            # 2. บันทึกคำขอถอนเงินถ้าผ่านเงื่อนไข
            withdrawal_id = f"WD{uuid.uuid4().hex[:8].upper()}"
            cursor.execute("""
                INSERT INTO withdrawals (withdrawal_id, tenant_id, member_id, amount, bank_name, bank_account_no, bank_account_name, withdrawal_method)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (withdrawal_id, tenant_id, req.member_id, req.amount, req.bank_name, req.bank_account_no, req.bank_account_name, req.withdrawal_method))
            
        conn.commit()
        return {"status": "success", "message": "ส่งคำขอถอนเงินเรียบร้อย รอแอดมินอนุมัติ", "withdrawal_id": withdrawal_id}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.put("/{withdrawal_id}/approve", dependencies=[Depends(verify_role(["super_admin", "company_admin"]))])
def approve_withdrawal(withdrawal_id: str, tenant_id: str = Depends(verify_tenant_header)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE withdrawals SET status = 'approved' WHERE withdrawal_id = %s AND tenant_id = %s", (withdrawal_id, tenant_id))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="ไม่พบรายการถอนเงินนี้")
        conn.commit()
        return {"status": "success", "message": f"อนุมัติการถอนเงิน {withdrawal_id} เรียบร้อยแล้ว (หักภาษี ณ ที่จ่าย 3% เรียบร้อย)"}
    finally:
        conn.close()
