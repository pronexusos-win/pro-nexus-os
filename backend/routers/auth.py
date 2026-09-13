from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.auth.auth_engine import verify_pin, create_access_token
from core.database import get_db_connection

router = APIRouter()

class LoginRequest(BaseModel):
    line_user_id: str
    pin: str

@router.post("/login")
def login(request: LoginRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ค้นหา user จาก LINE ID
            cursor.execute("SELECT * FROM members WHERE line_user_id = %s", (request.line_user_id,))
            user = cursor.fetchone()
            
            if not user or not user["pin_hash"]:
                raise HTTPException(status_code=401, detail="ไม่พบผู้ใช้งาน หรือ รหัส PIN ไม่ถูกต้อง")
            
            # ตรวจสอบ PIN
            if not verify_pin(request.pin, user["pin_hash"]):
                raise HTTPException(status_code=401, detail="รหัส PIN ไม่ถูกต้อง")
                
            # สร้าง JWT Token พร้อมฝัง Role และ Tenant
            token_payload = {
                "sub": user["member_id"],
                "role": user["role"],
                "tenant_id": user["tenant_id"],
                "name": user["name"]
            }
            access_token = create_access_token(data=token_payload)
            
            return {
                "status": "success",
                "message": "Login successful",
                "access_token": access_token,
                "token_type": "bearer",
                "user_info": {
                    "name": user["name"],
                    "role": user["role"],
                    "tenant_id": user["tenant_id"]
                }
            }
    finally:
        conn.close()
