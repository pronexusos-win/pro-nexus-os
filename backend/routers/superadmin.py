from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json
from middleware.rbac import verify_role
from core.database import get_db_connection

router = APIRouter()

class ModuleToggleRequest(BaseModel):
    unilevel: bool
    cashback: bool
    company_fund: bool

@router.put("/tenants/{tenant_id}/modules", dependencies=[Depends(verify_role(["super_admin"]))])
def toggle_tenant_modules(tenant_id: str, config: ModuleToggleRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            modules_json = json.dumps(config.dict())
            cursor.execute("UPDATE tenants SET modules = %s WHERE tenant_id = %s", (modules_json, tenant_id))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Tenant not found")
        conn.commit()
        return {"status": "success", "message": f"อัปเดตโมดูลให้ {tenant_id} เรียบร้อย", "active_modules": config.dict()}
    finally:
        conn.close()
