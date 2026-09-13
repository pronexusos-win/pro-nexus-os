from fastapi import APIRouter, Depends
from pydantic import BaseModel
import uuid
from middleware.rbac import verify_role
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

class TrackingUpdate(BaseModel):
    tracking_no: str
    courier: str

@router.put("/{order_id}/update-tracking", dependencies=[Depends(verify_role(["super_admin", "company_admin"]))])
def update_tracking(order_id: str, req: TrackingUpdate, tenant_id: str = Depends(verify_tenant_header)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE orders SET tracking_no = %s, courier = %s, status = 'shipped' 
                WHERE order_id = %s AND tenant_id = %s
            """, (req.tracking_no, req.courier, order_id, tenant_id))
        conn.commit()
        return {"status": "success", "message": f"อัปเดต Tracking {req.tracking_no} เรียบร้อย"}
    finally:
        conn.close()
