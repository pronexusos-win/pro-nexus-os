from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from backend.app.core.database import get_db_connection

router = APIRouter(prefix="/api/v1/products", tags=["Products"])

class ProductResponse(BaseModel):
    id: int
    company_slug: str
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int
    image_url: Optional[str] = None
    category: str

@router.get("/", response_model=List[ProductResponse])
def get_products(
    company: str = Query(default="tp_extra", description="รหัสบริษัท เช่น tp_extra"),
    category: Optional[str] = Query(default=None, description="กรองตามหมวดหมู่")
):
    query = """
        SELECT id, company_slug, name, description, CAST(price AS FLOAT) AS price, 
               stock_quantity, image_url, category
        FROM products
        WHERE company_slug = %s AND is_active = 1
    """
    params = [company]

    if category:
        query += " AND category = %s"
        params.append(category)

    query += " ORDER BY id ASC;"

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                products = cursor.fetchall()
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
