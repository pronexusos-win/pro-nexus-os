from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

class ConfigUpdateModel(BaseModel):
    cash_point_ratio: float
    shop_point_ratio: float
    welfare_fund_deduction: float
    min_purchase_for_welfare: float
    cash_withdrawal_min: float
    is_system_active: bool
    super_admin_id: str

class ProfileForceEditModel(BaseModel):
    target_user_id: str
    new_first_name: str
    new_last_name: str
    new_phone: str
    new_sponsor_id: Optional[str] = None # แก้ไขสายงาน กรณีคนสมัครกรอกรหัสผู้แนะนำผิด!
    super_admin_id: str

@router.put("/super-admin/config/update")
def update_tenant_rules(config: ConfigUpdateModel, tenant_id: str = Depends(verify_tenant_header)):
    """(God Mode) เปลี่ยนแปลงกติกาธุรกิจ (เช่น % แต้ม, ยอดขั้นต่ำ) มีผลทันทีกับบิลถัดไป"""
    # หมายเหตุ: ในระบบจริงต้องมี Middleware เช็ก Role ว่าเป็น Super Admin ถึงจะยิง API นี้ได้
    if config.cash_point_ratio + config.shop_point_ratio != 100:
        raise HTTPException(status_code=400, detail="สัดส่วน Cash และ Shop รวมกันต้องได้ 100%")

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE tenant_configurations 
                SET cash_point_ratio = %s, shop_point_ratio = %s, 
                    welfare_fund_deduction = %s, min_purchase_for_welfare = %s, 
                    cash_withdrawal_min = %s, is_system_active = %s, updated_by = %s
                WHERE tenant_id = %s
            """, (config.cash_point_ratio, config.shop_point_ratio, config.welfare_fund_deduction, 
                  config.min_purchase_for_welfare, config.cash_withdrawal_min, 
                  config.is_system_active, config.super_admin_id, tenant_id))
        conn.commit()
        return {"status": "success", "message": "อัปเดตกติกาทางธุรกิจของระบบเรียบร้อยแล้ว"}
    finally:
        conn.close()

@router.put("/super-admin/profile/force-edit")
def force_edit_user_profile(profile: ProfileForceEditModel, tenant_id: str = Depends(verify_tenant_header)):
    """(God Mode) ทะลวงเข้าไปแก้ไขข้อมูลส่วนตัวสมาชิก หรือย้ายสายงาน (Upline) เมื่อเกิดข้อผิดพลาด"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. แก้ไขข้อมูลพื้นฐาน (ชื่อ, เบอร์โทร)
            cursor.execute("""
                UPDATE users 
                SET first_name = %s, last_name = %s, phone = %s 
                WHERE user_id = %s AND tenant_id = %s
            """, (profile.new_first_name, profile.new_last_name, profile.new_phone, profile.target_user_id, tenant_id))
            
            # 2. แก้ไขสายงาน (ถ้ามีการส่ง new_sponsor_id มา)
            if profile.new_sponsor_id:
                cursor.execute("""
                    UPDATE affiliate_tree 
                    SET sponsor_id = %s 
                    WHERE user_id = %s AND tenant_id = %s
                """, (profile.new_sponsor_id, profile.target_user_id, tenant_id))
                
        conn.commit()
        return {"status": "success", "message": f"แก้ไขโปรไฟล์ของรหัส {profile.target_user_id} สำเร็จ (รวมการย้ายสายงาน)"}
    finally:
        conn.close()
