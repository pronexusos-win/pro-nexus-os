from fastapi import Header, HTTPException

def verify_tenant_header(x_tenant_id: str = Header(...)):
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required for multi-tenant isolation")
    # ในระบบจริงสามารถ query เช็คสถานะ Tenant จากฐานข้อมูลตรงนี้ได้
    return x_tenant_id
