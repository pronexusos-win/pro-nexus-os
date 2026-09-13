from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid
from services.compliance_engine import process_split_and_tax
from services.commission_engine import calculate_unilevel_plan
from services.affiliate.tree_engine import get_upline_chain
from services.notifications.line_notify import send_line_notification
from core.database import get_db_connection
from middleware.tenant import verify_tenant_header

router = APIRouter()

class OrderTransaction(BaseModel):
    member_id: str
    sale_amount: float
    plan_type: str = "unilevel"  # รองรับ "unilevel" หรือ "single_tier" สำหรับ Tenant อื่น

@router.post("/process-order-commissions")
def process_order_commissions(transaction: OrderTransaction, tenant_id: str = Depends(verify_tenant_header)):
    # ตรวจสอบแผน: ถ้าเป็น single_tier จ่ายชั้นเดียว (เช่น ลัคกิโอ) ถ้า unilevel จ่ายตามโครงสร้างสายงาน
    if transaction.plan_type == "single_tier":
        raw_payouts = [{"level": 1, "gross_amount": transaction.sale_amount * 0.10}]
        max_depth = 1
    else:
        raw_payouts = calculate_unilevel_plan(transaction.sale_amount)
        max_depth = 4
        
    actual_uplines = get_upline_chain(transaction.member_id, max_depth=max_depth)
    
    processed_records = []
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for index, payout in enumerate(raw_payouts):
                level = payout["level"]
                gross = payout["gross_amount"]
                
                if index < len(actual_uplines):
                    receiver_id = actual_uplines[index]["member_id"]
                    receiver_name = actual_uplines[index]["name"]
                else:
                    receiver_id = f"company_pool_lvl_{level}"
                    receiver_name = f"ส่วนกลาง {tenant_id}"
                
                # ประมวลผล Split 80/20 และหักภาษี 3%
                financials = process_split_and_tax(gross)
                txn_id = f"txn_{uuid.uuid4().hex[:10]}"
                
                # บันทึกลง General Ledger รองรับภาษีและการตรวจสอบ
                sql = """
                INSERT INTO commissions 
                (transaction_id, member_id, gross_amount, tax_amount, net_amount, type) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    txn_id, 
                    receiver_id, 
                    financials["gross_commission"], 
                    financials["withholding_tax_3"], 
                    financials["net_cash_payable"], 
                    transaction.plan_type
                ))
                
                # จำลองการส่งแจ้งเตือนยอดเงินแยกกระเป๋า
                msg = (
                    f"💰 คอมมิชชันเข้า! ยอดรวม: {financials['gross_commission']:,.2f} บ. | "
                    f"เงินสดสุทธิ (หักภาษี 3%): {financials['net_cash_payable']:,.2f} บ. | "
                    f"แต้มช้อปปิ้ง: {financials['shopping_wallet_20']:,.2f} P"
                )
                send_line_notification(msg, receiver_id)
                
                processed_records.append({
                    "receiver_name": receiver_name,
                    "level": level,
                    **financials
                })
                
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
        
    return {
        "status": "success",
        "tenant_id": tenant_id,
        "plan_type": transaction.plan_type,
        "summary": "ประมวลผลแยกกระเป๋า 80/20, หักภาษี ณ ที่จ่าย 3% และลงบันทึกบัญชีเสร็จสมบูรณ์",
        "records": processed_records
    }
