from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json
from middleware.rbac import verify_role
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

class BrandingRequest(BaseModel):
    theme_color: str
    logo_url: str
    company_name_th: str

@router.put("/branding", dependencies=[Depends(verify_role(["company_admin"]))])
def update_branding(config: BrandingRequest, tenant_id: str = Depends(verify_tenant_header)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            branding_json = json.dumps(config.dict())
            cursor.execute("UPDATE tenants SET branding = %s WHERE tenant_id = %s", (branding_json, tenant_id))
        conn.commit()
        return {"status": "success", "message": "อัปเดตหน้าตาบริษัทเรียบร้อย", "branding": config.dict()}
    finally:
        conn.close()
