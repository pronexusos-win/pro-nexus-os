from fastapi import APIRouter, Depends, HTTPException
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

@router.get("/products")
def get_products(tenant_id: str = Depends(verify_tenant_header)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT sku, name, price, stock FROM products WHERE tenant_id = %s", (tenant_id,))
            products = cursor.fetchall()
        return {"status": "success", "tenant_id": tenant_id, "products": products}
    finally:
        conn.close()
