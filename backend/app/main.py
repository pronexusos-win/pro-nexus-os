import os
import pymysql
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

app = FastAPI(title="TP Extra SaaS Platform - Production", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "rootpassword"),
    "database": os.getenv("DB_NAME", "saas_mlm_pos_db"),
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

class MemberRegisterRequest(BaseModel):
    company_id: str
    upline_id: str
    prefix: str
    first_name: str
    last_name: str
    citizen_id: str = Field(..., min_length=13, max_length=13)
    phone: str
    address_no: Optional[str] = ""
    moo: Optional[str] = ""
    soi_road: Optional[str] = ""
    province: Optional[str] = ""
    district: Optional[str] = ""
    subdistrict: Optional[str] = ""
    postcode: Optional[str] = ""
    bank_name: Optional[str] = ""
    bank_account_no: Optional[str] = ""
    email: Optional[str] = ""

class CartItem(BaseModel):
    product_id: str
    quantity: int
    price: float

class POSCheckoutRequest(BaseModel):
    company_id: str
    branch_id: str
    member_id: str
    payment_channel: str
    paid_cash: float = 0.00
    paid_cash_point: float = 0.00
    paid_shopping_point: float = 0.00
    items: List[CartItem]

class ResetRequest(BaseModel):
    company_id: str
    admin_password: str

@app.get("/api/tenant/config/{company_id}")
def get_tenant_config(company_id: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM companies WHERE company_id = %s", (company_id,))
            comp = cursor.fetchone()
            if not comp:
                raise HTTPException(status_code=404, detail="ไม่พบบริษัทนี้ในระบบ")
            return comp
    finally:
        conn.close()

@app.post("/api/members/register", status_code=status.HTTP_201_CREATED)
def register_member(req: MemberRegisterRequest):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT member_id FROM members WHERE company_id = %s AND member_id = %s", (req.company_id, req.upline_id))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="ไม่พบรหัสผู้แนะนำในระบบบริษัทนี้")

            cursor.execute("SELECT member_id FROM members WHERE company_id = %s AND citizen_id = %s", (req.company_id, req.citizen_id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="เลขบัตรประชาชนนี้เคยลงทะเบียนในบริษัทนี้แล้ว")

            cursor.execute("SELECT COUNT(*) as total FROM members WHERE company_id = %s FOR UPDATE", (req.company_id,))
            seq = cursor.fetchone()['total'] + 1
            prefix_id = req.company_id[:2].upper()
            new_member_id = f"{prefix_id}{seq:06d}"

            sql = """
                INSERT INTO members (
                    member_id, company_id, upline_id, prefix, first_name, last_name, citizen_id,
                    phone, address_no, moo, soi_road, province, district, subdistrict,
                    postcode, bank_name, bank_account_no, email
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                new_member_id, req.company_id, req.upline_id, req.prefix, req.first_name, req.last_name,
                req.citizen_id, req.phone, req.address_no, req.moo, req.soi_road,
                req.province, req.district, req.subdistrict, req.postcode,
                req.bank_name, req.bank_account_no, req.email
            ))
            conn.commit()
            return {"status": "success", "member_id": new_member_id, "message": "สมัครสมาชิกสำเร็จ"}
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/pos/checkout")
def pos_checkout(req: POSCheckoutRequest):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            total_amount = sum(item.quantity * item.price for item in req.items)
            order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"

            for item in req.items:
                cursor.execute(
                    "SELECT stock_quantity FROM branch_stocks WHERE company_id = %s AND branch_id = %s AND product_id = %s FOR UPDATE",
                    (req.company_id, req.branch_id, item.product_id)
                )
                stock_row = cursor.fetchone()
                if not stock_row or stock_row["stock_quantity"] < item.quantity:
                    raise HTTPException(status_code=400, detail=f"สินค้า {item.product_id} ในสต็อกสาขาไม่เพียงพอ")
                
                cursor.execute(
                    "UPDATE branch_stocks SET stock_quantity = stock_quantity - %s WHERE company_id = %s AND branch_id = %s AND product_id = %s",
                    (item.quantity, req.company_id, req.branch_id, item.product_id)
                )

            cursor.execute("""
                INSERT INTO orders (order_id, company_id, branch_id, member_id, total_amount, payment_channel)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (order_id, req.company_id, req.branch_id, req.member_id, total_amount, req.payment_channel))

            one_percent = total_amount * 0.01
            cash_slice = round(one_percent * 0.80, 2)
            shop_slice = round(one_percent * 0.20, 2)

            cursor.execute("""
                UPDATE members SET cash_point = cash_point + %s, shopping_point = shopping_point + %s 
                WHERE company_id = %s AND member_id = %s
            """, (cash_slice, shop_slice, req.company_id, req.member_id))
            cursor.execute("""
                INSERT INTO point_transactions (company_id, order_id, member_id, generation, cash_point_added, shopping_point_added, txn_type)
                VALUES (%s, %s, %s, 0, %s, %s, 'COMMISSION')
            """, (req.company_id, order_id, req.member_id, cash_slice, shop_slice))

            curr_member = req.member_id
            for gen in range(1, 5):
                cursor.execute("SELECT upline_id FROM members WHERE company_id = %s AND member_id = %s", (req.company_id, curr_member))
                row = cursor.fetchone()
                if not row or not row["upline_id"]:
                    break
                curr_upline = row["upline_id"]
                
                cursor.execute("""
                    UPDATE members SET cash_point = cash_point + %s, shopping_point = shopping_point + %s 
                    WHERE company_id = %s AND member_id = %s
                """, (cash_slice, shop_slice, req.company_id, curr_upline))
                cursor.execute("""
                    INSERT INTO point_transactions (company_id, order_id, member_id, generation, cash_point_added, shopping_point_added, txn_type)
                    VALUES (%s, %s, %s, %s, %s, %s, 'COMMISSION')
                """, (req.company_id, order_id, curr_upline, gen, cash_slice, shop_slice))
                
                curr_member = curr_upline

            conn.commit()
            return {"status": "success", "order_id": order_id, "total_amount": total_amount, "message": "ชำระเงินและปันผล 5 ชั้นสำเร็จ"}
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/admin/system/reset")
def reset_company_data(req: ResetRequest):
    if req.admin_password != "CLEAN2026":
        raise HTTPException(status_code=403, detail="รหัสผ่าน Super Admin ไม่ถูกต้อง")
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM point_transactions WHERE company_id = %s", (req.company_id,))
            cursor.execute("DELETE FROM orders WHERE company_id = %s", (req.company_id,))
            cursor.execute("UPDATE branch_stocks SET stock_quantity = 0 WHERE company_id = %s", (req.company_id,))
            cursor.execute("DELETE FROM members WHERE company_id = %s AND role != 'COMPANY_ADMIN'", (req.company_id,))
            cursor.execute("UPDATE members SET cash_point = 0, shopping_point = 0 WHERE company_id = %s AND role = 'COMPANY_ADMIN'", (req.company_id,))
            conn.commit()
            return {"status": "success", "message": "ล้างข้อมูลระบบเรียบร้อย พร้อมใช้งานจริง"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()