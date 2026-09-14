import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from backend.app.core.database import get_db_connection

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])

class CreateOrderRequest(BaseModel):
    company_slug: str = Field(default="tp_extra")
    line_user_id: str
    total_amount: float
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    shipping_address: Optional[str] = None

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_order(payload: CreateOrderRequest):
    order_no = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    insert_sql = """
        INSERT INTO orders (
            order_no, company_slug, line_user_id, 
            customer_name, customer_phone, shipping_address, 
            total_amount, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending_payment');
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(insert_sql, (
                    order_no,
                    payload.company_slug,
                    payload.line_user_id,
                    payload.customer_name,
                    payload.customer_phone,
                    payload.shipping_address,
                    payload.total_amount
                ))
            conn.commit()

        return {
            "status": "success",
            "message": "Order created successfully",
            "data": {
                "order_no": order_no,
                "company_slug": payload.company_slug,
                "line_user_id": payload.line_user_id,
                "customer_name": payload.customer_name,
                "customer_phone": payload.customer_phone,
                "shipping_address": payload.shipping_address,
                "total_amount": payload.total_amount,
                "status": "pending_payment"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

@router.get("/user/{line_user_id}")
def get_user_orders(line_user_id: str, company: str = Query(default="tp_extra")):
    query = """
        SELECT order_no, total_amount, status, customer_name, customer_phone, shipping_address,
               DATE_FORMAT(created_at, '%d/%m/%Y %H:%i') AS created_at
        FROM orders
        WHERE line_user_id = %s AND company_slug = %s
        ORDER BY id DESC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (line_user_id, company))
                orders = cursor.fetchall()
        return {"status": "success", "orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
