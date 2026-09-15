import os
from fastapi import APIRouter, HTTPException, Query, Header, status
from pydantic import BaseModel, Field
from typing import Optional
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from backend.app.core.database import get_db_connection

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Dashboard"])

ADMIN_PASSCODE = os.getenv("ADMIN_PASSCODE", "admin1234")

# โหลด Access Token สำหรับแต่ละบริษัท (มี Fallback ให้ TP Extra)
COMPANY_TOKENS = {
    "tp_extra": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_TP_EXTRA"),
    "pro_nexus": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_PRO_NEXUS"),
    "luck_kio": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_LUCK_KIO"),
    "peak_icon": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_PEAK_ICON")
}

class LoginRequest(BaseModel):
    passcode: str

class UpdateOrderStatusRequest(BaseModel):
    status: str = Field(..., example="shipping")
    tracking_number: Optional[str] = None

def verify_admin(x_admin_key: Optional[str] = Header(None)):
    if not x_admin_key or x_admin_key != ADMIN_PASSCODE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="รหัสผ่านผู้ดูแลระบบไม่ถูกต้องหรือไม่ได้รับอนุญาต"
        )

def send_line_push_notification(company_slug: str, line_user_id: str, message_text: str):
    """ส่ง Push Message หาผู้ใช้ผ่าน LINE Messaging API"""
    token = COMPANY_TOKENS.get(company_slug)
    if not token or line_user_id.startswith("U_GUEST"):
        return
    try:
        conf = Configuration(access_token=token)
        with ApiClient(conf) as api_client:
            line_api = MessagingApi(api_client)
            line_api.push_message(
                PushMessageRequest(
                    to=line_user_id,
                    messages=[TextMessage(text=message_text)]
                )
            )
    except Exception as e:
        print(f"⚠️ ไม่สามารถส่ง LINE Push Message: {e}")

@router.post("/verify-passcode")
def verify_passcode(payload: LoginRequest):
    if payload.passcode == ADMIN_PASSCODE:
        return {"status": "success", "token": ADMIN_PASSCODE}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passcode ไม่ถูกต้อง")

@router.get("/overview")
def get_dashboard_overview(company: str = Query(default="tp_extra"), x_admin_key: Optional[str] = Header(None)):
    verify_admin(x_admin_key)
    
    stats_query = """
        SELECT 
            COUNT(CASE WHEN status = 'paid' THEN 1 END) AS paid_orders,
            COUNT(CASE WHEN status = 'pending_payment' THEN 1 END) AS pending_orders,
            COUNT(CASE WHEN status = 'shipping' THEN 1 END) AS shipping_orders,
            COALESCE(SUM(CASE WHEN status = 'paid' THEN total_amount ELSE 0 END), 0) AS total_revenue
        FROM orders
        WHERE company_slug = %s;
    """
    recent_orders_query = """
        SELECT o.order_no, o.line_user_id, o.customer_name, o.customer_phone, o.shipping_address, CAST(o.total_amount AS FLOAT) AS total_amount, o.status, 
               s.image_url AS slip_url, CAST(s.trans_amount AS FLOAT) AS slip_amount,
               DATE_FORMAT(o.created_at, '%d/%m/%Y %H:%i') AS created_at
        FROM orders o
        LEFT JOIN slips s ON o.slip_id = s.id
        WHERE o.company_slug = %s
        ORDER BY o.id DESC LIMIT 50;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(stats_query, (company,))
                stats = cursor.fetchone()
                
                cursor.execute(recent_orders_query, (company,))
                orders = cursor.fetchall()

        return {"status": "success", "stats": stats, "orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/orders/{order_no}/status")
def update_order_status(order_no: str, payload: UpdateOrderStatusRequest, x_admin_key: Optional[str] = Header(None)):
    verify_admin(x_admin_key)

    valid_statuses = ["pending_payment", "paid", "shipping", "completed", "cancelled"]
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    find_order_sql = "SELECT line_user_id, company_slug, total_amount FROM orders WHERE order_no = %s;"
    update_sql = "UPDATE orders SET status = %s, updated_at = NOW() WHERE order_no = %s;"

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(find_order_sql, (order_no,))
                order = cursor.fetchone()
                if not order:
                    raise HTTPException(status_code=404, detail="Order not found")

                cursor.execute(update_sql, (payload.status, order_no))
            conn.commit()

        # ส่ง Push Notification ไปยัง LINE ลูกค้าตามสถานะใหม่
        if payload.status == "shipping":
            track_txt = f"\n📦 เลขพัสดุ: {payload.tracking_number}" if payload.tracking_number else ""
            msg = f"🚚 สินค้าของคุณกำลังจัดส่ง!\n\nรหัสออเดอร์: {order_no}{track_txt}\nขอบคุณที่อุดหนุนสินค้า BAENGPUN แบ่งปันชอป ครับ"
            send_line_push_notification(order["company_slug"], order["line_user_id"], msg)

        elif payload.status == "completed":
            msg = f"🎉 คำสั่งซื้อ {order_no} จัดส่งสำเร็จเรียบร้อยแล้ว\nหวังว่าจะประทับใจในสินค้าของเราครับ"
            send_line_push_notification(order["company_slug"], order["line_user_id"], msg)

        return {"status": "success", "order_no": order_no, "new_status": payload.status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BatchStatusUpdateRequest(BaseModel):
    order_nos: list[str]
    status: str
    tracking_prefix: Optional[str] = None

@router.post("/orders/batch-status")
def batch_update_order_status(
    payload: BatchStatusUpdateRequest,
    admin_key: str = Depends(verify_admin_key)
):
    if not payload.order_nos:
        raise HTTPException(status_code=400, detail="No orders provided")

    format_strings = ",".join(["%s"] * len(payload.order_nos))
    update_sql = f"""
        UPDATE orders
        SET status = %s, updated_at = NOW()
        WHERE order_no IN ({format_strings});
    """
    params = [payload.status] + payload.order_nos

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(update_sql, params)
                affected = cursor.rowcount
            conn.commit()
        return {
            "status": "success",
            "message": f"Updated {affected} orders to {payload.status}",
            "affected_rows": affected
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import io
import pandas as pd
from fastapi import UploadFile, File
from linebot.v3.messaging import PushMessageRequest, TextMessage, Configuration, ApiClient, MessagingApi

COMPANY_ACCESS_TOKENS = {
    "tp_extra": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_TP_EXTRA"),
    "pro_nexus": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_PRO_NEXUS"),
    "luck_kio": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_LUCK_KIO"),
    "peak_icon": os.getenv("LINE_CHANNEL_ACCESS_TOKEN_PEAK_ICON")
}

@router.post("/orders/import-tracking")
async def import_tracking_file(
    file: UploadFile = File(...),
    company: str = Query(default="tp_extra"),
    admin_key: str = Depends(verify_admin_key)
):
    contents = await file.read()
    filename = file.filename.lower()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents), dtype=str)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents), dtype=str)
        else:
            raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ .csv, .xlsx หรือ .xls เท่านั้น")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"อ่านไฟล์ไม่สำเร็จ: {str(e)}")

    # ตรวจหาคอลัมน์ Order No และ Tracking Number
    col_mapping = {}
    for col in df.columns:
        c_clean = str(col).strip().lower().replace(" ", "").replace("_", "")
        if c_clean in ["orderno", "order", "รหัสออเดอร์", "เลขออเดอร์"]:
            col_mapping["order_no"] = col
        elif c_clean in ["trackingnumber", "tracking", "เลขพัสดุ", "trackingno", "แทร็กกิ้ง"]:
            col_mapping["tracking_number"] = col

    if "order_no" not in col_mapping or "tracking_number" not in col_mapping:
        raise HTTPException(
            status_code=400, 
            detail="ไม่พบคอลัมน์ที่ถูกต้อง ไฟล์ต้องมีหัวตาราง: รหัสออเดอร์ (order_no) และ เลขพัสดุ (tracking_number)"
        )

    token = COMPANY_ACCESS_TOKENS.get(company) or os.getenv("LINE_CHANNEL_ACCESS_TOKEN_TP_EXTRA")
    messaging_api = None
    if token:
        conf = Configuration(access_token=token)
        messaging_api = MessagingApi(ApiClient(conf))

    updated_count = 0
    pushed_count = 0
    errors = []

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for _, row in df.iterrows():
                order_no = str(row[col_mapping["order_no"]]).strip() if pd.notna(row[col_mapping["order_no"]]) else ""
                tracking = str(row[col_mapping["tracking_number"]]).strip() if pd.notna(row[col_mapping["tracking_number"]]) else ""

                if not order_no or not tracking or order_no.lower() == "nan":
                    continue

                # อัปเดตสถานะและเลขแทร็กกิ้ง
                cursor.execute(
                    """
                    UPDATE orders 
                    SET tracking_number = %s, status = shipping, updated_at = NOW() 
                    WHERE order_no = %s AND company_slug = %s;
                    """,
                    (tracking, order_no, company)
                )
                if cursor.rowcount > 0:
                    updated_count += 1

                    # ดึง line_user_id เพื่อยิง Push Notification
                    cursor.execute("SELECT line_user_id, customer_name FROM orders WHERE order_no = %s;", (order_no,))
                    order_info = cursor.fetchone()
                    if order_info and order_info.get("line_user_id") and messaging_api:
                        line_uid = order_info["line_user_id"]
                        cust_name = order_info.get("customer_name") or "คุณลูกค้า"
                        msg_text = (
                            f"📦 แจ้งเตือนการจัดส่งสินค้า\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"เรียน {cust_name}\n"
                            f"คำสั่งซื้อรหัส: {order_no}\n"
                            f"ได้ถูกจัดส่งเรียบร้อยแล้วครับ\n\n"
                            f"🚚 เลขพัสดุ: {tracking}\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"ขอบคุณที่ไว้วางใจอุดหนุนสินค้ากับเราครับ 🙏"
                        )
                        try:
                            messaging_api.push_message(
                                PushMessageRequest(
                                    to=line_uid,
                                    messages=[TextMessage(text=msg_text)]
                                )
                            )
                            pushed_count += 1
                        except Exception as pe:
                            errors.append(f"{order_no}: Push failed ({str(pe)})")
        conn.commit()

    return {
        "status": "success",
        "message": f"อัปเดตเลขพัสดุสำเร็จ {updated_count} รายการ, แจ้งเตือนผ่าน LINE สำเร็จ {pushed_count} รายการ",
        "updated_count": updated_count,
        "pushed_count": pushed_count,
        "errors": errors
    }


class ScanPackRequest(BaseModel):
    order_no: str
    company_slug: str = "tp_extra"

@router.post("/orders/scan-pack")
def scan_pack_order(payload: ScanPackRequest, admin_key: str = Depends(verify_admin_key)):
    order_no = payload.order_no.strip()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, order_no, customer_name, customer_phone, shipping_address, 
                       total_amount, status, company_slug
                FROM orders 
                WHERE order_no = %s AND company_slug = %s;
                """,
                (order_no, payload.company_slug)
            )
            order = cursor.fetchone()
            if not order:
                raise HTTPException(status_code=404, detail=f"ไม่พบออเดอร์ {order_no}")

            if order["status"] == "pending_payment":
                raise HTTPException(status_code=400, detail=f"ออเดอร์นี้ยังไม่ชำระเงิน (สถานะ: {order['status']})")

            # อัปเดตสถานะเป็น packed เพื่อระบุว่าตรวจและบรรจุกล่องแล้ว
            cursor.execute(
                """
                UPDATE orders 
                SET status = 'packed', updated_at = NOW() 
                WHERE order_no = %s;
                """,
                (order_no,)
            )
            conn.commit()

    return {
        "status": "success",
        "message": f"ตรวจเช็กและแพ็กออเดอร์ {order_no} สำเร็จ",
        "order": order
    }


@router.get("/orders/handover-list")
def get_handover_list(
    company: str = Query(default="tp_extra"),
    admin_key: str = Depends(verify_admin_key)
):
    query = """
        SELECT order_no, customer_name, customer_phone, shipping_address, 
               tracking_number, CAST(total_amount AS FLOAT) as total_amount, 
               status, DATE_FORMAT(updated_at, '%d/%m/%Y %H:%i') AS packed_time
        FROM orders
        WHERE company_slug = %s AND status IN ('packed', 'paid')
        ORDER BY id ASC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (company,))
            orders = cursor.fetchall()

    return {
        "status": "success",
        "company_slug": company,
        "total_parcels": len(orders),
        "orders": orders
    }

class HandoverConfirmRequest(BaseModel):
    order_nos: list[str]
    carrier_name: Optional[str] = "FLASH_EXPRESS"
    driver_name: Optional[str] = None

@router.post("/orders/handover-confirm")
def confirm_handover(
    payload: HandoverConfirmRequest,
    admin_key: str = Depends(verify_admin_key)
):
    if not payload.order_nos:
        raise HTTPException(status_code=400, detail="ไม่พบรายการออเดอร์สำหรับส่งมอบ")

    format_strings = ",".join(["%s"] * len(payload.order_nos))
    update_sql = f"""
        UPDATE orders
        SET status = 'shipping', updated_at = NOW()
        WHERE order_no IN ({format_strings});
    """

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(update_sql, payload.order_nos)
            affected = cursor.rowcount
        conn.commit()

    return {
        "status": "success",
        "message": f"ส่งมอบพัสดุให้ {payload.carrier_name} สำเร็จ {affected} กล่อง",
        "affected_rows": affected
    }


class UpdateStockRequest(BaseModel):
    sku: str
    quantity: int
    low_stock_threshold: Optional[int] = None

@router.get("/products/inventory")
def get_inventory(company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, sku, name, CAST(price AS FLOAT) as price, 
                       stock_quantity, low_stock_threshold,
                       DATE_FORMAT(updated_at, '%d/%m/%Y %H:%i') as updated_at
                FROM products 
                WHERE company_slug = %s
                ORDER BY stock_quantity ASC;
                """,
                (company,)
            )
            products = cursor.fetchall()
    return {"status": "success", "products": products}

@router.post("/products/update-stock")
def update_product_stock(payload: UpdateStockRequest, company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if payload.low_stock_threshold is not None:
                cursor.execute(
                    """
                    UPDATE products 
                    SET stock_quantity = %s, low_stock_threshold = %s, updated_at = NOW() 
                    WHERE sku = %s AND company_slug = %s;
                    """,
                    (payload.quantity, payload.low_stock_threshold, payload.sku, company)
                )
            else:
                cursor.execute(
                    """
                    UPDATE products 
                    SET stock_quantity = %s, updated_at = NOW() 
                    WHERE sku = %s AND company_slug = %s;
                    """,
                    (payload.quantity, payload.sku, company)
                )
        conn.commit()
    return {"status": "success", "message": f"อัปเดตสต็อก SKU {payload.sku} เป็น {payload.quantity} เรียบร้อย"}


@router.get("/orders/{order_no}/check-status")
def check_order_status(order_no: str):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT o.order_no, o.status, o.total_amount, o.customer_name,
                       s.cost_amount, s.shop_fee, s.member_points_cashback, s.net_profit
                FROM orders o
                LEFT JOIN order_splits s ON o.order_no = s.order_no
                WHERE o.order_no = %s;
                """,
                (order_no,)
            )
            order = cursor.fetchone()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"status": "success", "order": order}

@router.get("/financial-summary")
def get_financial_summary(company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    summary_sql = """
        SELECT 
            COUNT(*) as total_orders,
            COALESCE(SUM(total_amount), 0) as total_revenue,
            COALESCE(SUM(cost_amount), 0) as total_cost,
            COALESCE(SUM(shop_fee), 0) as total_shop_fee,
            COALESCE(SUM(member_points_cashback), 0) as total_points,
            COALESCE(SUM(net_profit), 0) as total_net_profit
        FROM order_splits
        WHERE company_slug = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(summary_sql, (company,))
            summary = cursor.fetchone()
    return {"status": "success", "summary": summary}


@router.get("/financial/escrow-summary")
def get_financial_escrow_summary(company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_orders,
                    COALESCE(SUM(total_gross_amount), 0) as total_gmv,
                    COALESCE(SUM(supplier_cost_payable), 0) as locked_supplier_pool,
                    COALESCE(SUM(branch_operating_share), 0) as branch_pool,
                    COALESCE(SUM(utility_reserve_accrual), 0) as utility_pool,
                    COALESCE(SUM(marketing_commission), 0) as commission_pool,
                    COALESCE(SUM(platform_net_gp), 0) as platform_gp,
                    COALESCE(SUM(platform_vat_amount), 0) as platform_vat
                FROM order_financial_splits
                WHERE company_slug = %s;
                """,
                (company,)
            )
            splits = cursor.fetchone()

            # ดึงสถานะกองทุนน้ำไฟ
            cursor.execute("SELECT * FROM branch_utility_funds WHERE company_slug = %s LIMIT 1;", (company,))
            utility = cursor.fetchone()

    return {
        "status": "success",
        "splits": splits,
        "utility_fund": utility
    }

@router.get("/financial/supplier-portal")
def get_supplier_portal_data(supplier_code: str = "SUP-BP-001"):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM suppliers WHERE supplier_code = %s;", (supplier_code,))
            supplier = cursor.fetchone()
            if not supplier:
                raise HTTPException(status_code=404, detail="ไม่พบข้อมูลซัพพลายเออร์")

            cursor.execute(
                """
                SELECT 
                    COALESCE(SUM(CASE WHEN supplier_payout_status = 'LOCKED_IN_ESCROW' THEN supplier_cost_payable ELSE 0 END), 0) as locked_in_escrow,
                    COALESCE(SUM(CASE WHEN supplier_payout_status = 'SETTLED_PAID' THEN supplier_cost_payable ELSE 0 END), 0) as settled_paid_total,
                    COUNT(id) as total_orders_supplied
                FROM order_financial_splits
                WHERE supplier_code = %s;
                """,
                (supplier_code,)
            )
            finance = cursor.fetchone()

            cursor.execute(
                """
                SELECT order_no, total_gross_amount, supplier_cost_payable, payout_due_date, supplier_payout_status
                FROM order_financial_splits
                WHERE supplier_code = %s
                ORDER BY id DESC LIMIT 10;
                """,
                (supplier_code,)
            )
            recent_bills = cursor.fetchall()

    return {
        "status": "success",
        "supplier": supplier,
        "finance": finance,
        "recent_bills": recent_bills
    }


class BlindShiftCloseRequest(BaseModel):
    branch_id: str = "HEADQUARTER"
    company_slug: str = "tp_extra"
    cashier_emp_code: str
    witness_emp_code: str
    b1000: int = 0
    b500: int = 0
    b100: int = 0
    b50: int = 0
    b20: int = 0
    coins: float = 0.0

@router.post("/security/close-shift-blind")
def close_shift_blind(payload: BlindShiftCloseRequest):
    # คำนวณยอดเงินสดที่นับจริง
    declared = (
        (payload.b1000 * 1000) +
        (payload.b500 * 500) +
        (payload.b100 * 100) +
        (payload.b50 * 50) +
        (payload.b20 * 20) +
        payload.coins
    )

    today = datetime.now().date()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # ดึงยอดเงินสดที่ระบบบันทึกจริงในวันนี้ (เฉพาะคำสั่งซื้อหน้าร้านที่เป็นเงินสด)
            cursor.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) as expected_cash
                FROM orders
                WHERE company_slug = %s AND status = 'paid' 
                  AND DATE(created_at) = %s AND shipping_address LIKE '%หน้าร้าน%';
                """,
                (payload.company_slug, today)
            )
            row = cursor.fetchone()
            expected = float(row["expected_cash"]) if row else 0.0
            variance = declared - expected
            is_investigate = abs(variance) > 20.0  # ต่างเกิน 20 บาท บังคับสอบสวน

            cursor.execute(
                """
                INSERT INTO shift_cash_reconciliations (
                    branch_id, company_slug, shift_date, cashier_emp_code, witness_emp_code,
                    system_expected_cash, cashier_declared_cash, variance_amount, is_investigation_required
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (payload.branch_id, payload.company_slug, today, payload.cashier_emp_code,
                 payload.witness_emp_code, expected, declared, variance, is_investigate)
            )
        conn.commit()

    return {
        "status": "success",
        "declared_total": declared,
        "variance": variance,
        "is_investigation_required": is_investigate,
        "message": "ปิดกะและบันทึกยอดเงินสดตาบอดเข้าสู่ระบบเรียบร้อย"
    }

class DualAuthVoidRequest(BaseModel):
    order_no: str
    company_slug: str = "tp_extra"
    branch_id: str = "HEADQUARTER"
    cashier_emp_code: str
    manager_passcode: str
    reason: str

@router.post("/security/authorize-void")
def authorize_void_with_audit(payload: DualAuthVoidRequest):
    # รหัสผู้จัดการสาขาสำหรับอนุมัติ (Security Barrier)
    if payload.manager_passcode != "9999":
        raise HTTPException(status_code=403, detail="รหัสผ่านผู้จัดการ (Manager Passcode) ไม่ถูกต้อง ไม่อนุมัติการยกเลิก")

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT order_no, status, total_amount FROM orders WHERE order_no = %s;", (payload.order_no,))
            order = cursor.fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="ไม่พบคำสั่งซื้อ")
            if order["status"] == "cancelled":
                raise HTTPException(status_code=400, detail="ออเดอร์นี้ถูกยกเลิกไปแล้ว")

            total_amt = float(order["total_amount"])

            # ปรับสถานะออเดอร์
            cursor.execute("UPDATE orders SET status = 'cancelled', updated_at = NOW() WHERE order_no = %s;", (payload.order_no,))

            # บันทึกประวัติความปลอดภัยแบบย้อนกลับไม่ได้
            cursor.execute(
                """
                INSERT INTO security_audit_logs (
                    company_slug, branch_id, emp_code, event_type, reference_no, details, manager_authorizer
                )
                VALUES (%s, %s, %s, 'VOID_ORDER', %s, %s, 'MGR-001');
                """,
                (payload.company_slug, payload.branch_id, payload.cashier_emp_code,
                 payload.order_no, f"ยกเลิกบิล ฿{total_amt:,.2f} เหตุผล: {payload.reason}")
            )
        conn.commit()

    return {
        "status": "success",
        "message": f"อนุมัติยกเลิกบิล {payload.order_no} โดยผู้จัดการ MGR-001 สำเร็จ พร้อมบันทึก Audit Log เรียบร้อย"
    }


class DeclareDividendRequest(BaseModel):
    declaration_no: str
    company_slug: str = "tp_extra"
    total_net_profit: float
    dividend_pool_amount: float
    resolution_date: str
    payout_date: str

@router.post("/corporate/declare-dividend")
def declare_and_calculate_dividend(payload: DeclareDividendRequest, admin_key: str = Depends(verify_admin_key)):
    # 1. คำนวณเงินสำรองตามกฎหมาย 5% ตามประมวลกฎหมายแพ่งและพาณิชย์ / พ.ร.บ. บริษัทมหาชน
    legal_reserve = round(payload.total_net_profit * 0.05, 2)
    max_distributable = payload.total_net_profit - legal_reserve
    if payload.dividend_pool_amount > max_distributable:
        raise HTTPException(
            status_code=400, 
            detail=f"ยอดปันผลเกินเพดานที่จัดสรรได้ (กำไรสุทธิหลังหักสำรองกฎหมาย 5% เหลือ ฿{max_distributable:,.2f})"
        )

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # ดึงหุ้นทั้งหมดของบริษัท
            cursor.execute("SELECT SUM(total_shares) as total_shares FROM shareholder_register WHERE company_slug = %s;", (payload.company_slug,))
            total_shares = cursor.fetchone()["total_shares"] or 0
            if total_shares <= 0:
                raise HTTPException(status_code=400, detail="ไม่พบจำนวนหุ้นในทะเบียนผู้ถือหุ้น")

            dps = round(payload.dividend_pool_amount / total_shares, 4)

            # บันทึก Declaration
            cursor.execute(
                """
                INSERT INTO dividend_declarations (
                    declaration_no, company_slug, agm_resolution_date, record_date, payout_date,
                    total_net_profit_declared, legal_reserve_allocated, total_dividend_pool, dividend_per_share
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE total_dividend_pool=VALUES(total_dividend_pool);
                """,
                (payload.declaration_no, payload.company_slug, payload.resolution_date, 
                 payload.resolution_date, payload.payout_date, payload.total_net_profit, 
                 legal_reserve, payload.dividend_pool_amount, dps)
            )

            # กระจายคำนวณภาษีหัก ณ ที่จ่าย 10% ให้ผู้ถือหุ้นแต่ละราย
            cursor.execute("SELECT shareholder_code, total_shares FROM shareholder_register WHERE company_slug = %s;", (payload.company_slug,))
            shareholders = cursor.fetchall()
            for sh in shareholders:
                gross = round(sh["total_shares"] * dps, 2)
                wht = round(gross * 0.10, 2)
                net = round(gross - wht, 2)
                cert_no = f"50TW-{payload.declaration_no}-{sh['shareholder_code']}"

                cursor.execute(
                    """
                    INSERT INTO shareholder_dividend_payouts (
                        declaration_no, shareholder_code, shares_held, 
                        gross_dividend, withholding_tax_10pct, net_payout_amount, tax_cert_no, paid_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW());
                    """,
                    (payload.declaration_no, sh["shareholder_code"], sh["total_shares"], gross, wht, net, cert_no)
                )

        conn.commit()

    return {
        "status": "success",
        "message": f"ประกาศและจัดสรรเงินปันผล {payload.declaration_no} สำเร็จ",
        "total_shares": total_shares,
        "dividend_per_share": dps,
        "legal_reserve_5pct": legal_reserve,
        "total_dividend_pool": payload.dividend_pool_amount
    }

@router.get("/corporate/governance-summary")
def get_corporate_governance_summary(company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM corporate_directors WHERE company_slug = %s;", (company,))
            directors = cursor.fetchall()
            cursor.execute("SELECT * FROM shareholder_register WHERE company_slug = %s;", (company,))
            shareholders = cursor.fetchall()
            cursor.execute("SELECT * FROM dividend_declarations WHERE company_slug = %s ORDER BY id DESC LIMIT 5;", (company,))
            declarations = cursor.fetchall()
    return {
        "status": "success",
        "directors": directors,
        "shareholders": shareholders,
        "recent_dividends": declarations
    }


from backend.app.services.compliance_guard import scan_text_compliance

class ComplianceCheckRequest(BaseModel):
    text_to_check: str

@router.post("/compliance/check-text")
def check_compliance_text(payload: ComplianceCheckRequest, admin_key: str = Depends(verify_admin_key)):
    result = scan_text_compliance(payload.text_to_check)
    return {
        "status": "success",
        "result": result
    }


class ProbationEvalRequest(BaseModel):
    emp_code: str
    milestone: str
    attendance_score: float
    accuracy_score: float
    service_score: float
    evaluator: str = "MGR-001"

class OffboardRequest(BaseModel):
    emp_code: str
    separation_type: str
    last_working_date: str
    notes: Optional[str] = "ส่งมอบงานเรียบร้อย"

@router.get("/hr/employees")
def get_hr_employees(company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, emp_code, company_slug, branch_id, full_name, id_card_no, phone,
                       DATE_FORMAT(hire_date, '%d/%m/%Y') as hire_date,
                       DATE_FORMAT(probation_end_date, '%d/%m/%Y') as probation_end_date,
                       DATEDIFF(probation_end_date, CURDATE()) as days_left_in_probation,
                       employment_status, job_position, CAST(base_salary AS FLOAT) as base_salary,
                       bank_name, bank_account_no, CAST(sso_deduction AS FLOAT) as sso_deduction
                FROM employee_master
                WHERE company_slug = %s
                ORDER BY days_left_in_probation ASC;
                """,
                (company,)
            )
            employees = cursor.fetchall()
    return {"status": "success", "employees": employees}

@router.post("/hr/evaluate-probation")
def evaluate_probation(payload: ProbationEvalRequest, admin_key: str = Depends(verify_admin_key)):
    total = round((payload.attendance_score + payload.accuracy_score + payload.service_score) / 3, 2)
    result = "PASS" if total >= 75.0 else ("NEEDS_IMPROVEMENT" if total >= 60.0 else "FAIL")

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO probation_reviews (
                    emp_code, milestone, attendance_score, accuracy_score, service_score, total_score, evaluation_result, evaluator
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (payload.emp_code, payload.milestone, payload.attendance_score, payload.accuracy_score, payload.service_score, total, result, payload.evaluator)
            )

            # หากผ่านการประเมินรอบตัดสิน ให้ปรับสถานะเป็นบรรจุ (CONFIRMED)
            if payload.milestone == "FINAL_110" and result == "PASS":
                cursor.execute("UPDATE employee_master SET employment_status = 'CONFIRMED' WHERE emp_code = %s;", (payload.emp_code,))
        conn.commit()

    return {
        "status": "success",
        "emp_code": payload.emp_code,
        "total_score": total,
        "result": result,
        "message": f"บันทึกการประเมิน {payload.milestone} สำเร็จ (คะแนนเฉลี่ย: {total}%)"
    }

@router.post("/hr/offboard-employee")
def offboard_employee(payload: OffboardRequest, admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. ระงับสถานะพนักงานทันที (Instant Revocation)
            new_status = "RESIGNED" if payload.separation_type == "RESIGNATION" else "TERMINATED"
            cursor.execute("UPDATE employee_master SET employment_status = %s WHERE emp_code = %s;", (new_status, payload.emp_code))

            # 2. บันทึกประวัติการเคลียร์งานและตัดสิทธิ์
            cursor.execute(
                """
                INSERT INTO offboarding_clearances (
                    emp_code, separation_type, last_working_date, cash_drawer_reconciled, keys_returned, system_access_revoked
                )
                VALUES (%s, %s, %s, TRUE, TRUE, TRUE);
                """,
                (payload.emp_code, payload.separation_type, payload.last_working_date)
            )
        conn.commit()

    return {
        "status": "success",
        "message": f"ดำเนินการตัดสิทธิ์เข้าระบบและทำเรื่องพ้นสภาพพนักงาน {payload.emp_code} สำเร็จ"
    }


class CloseDailyLedgerRequest(BaseModel):
    branch_id: str = "HEADQUARTER"
    company_slug: str = "tp_extra"
    manager_emp_code: str = "MGR-001"

@router.get("/settlement/daily-preview")
def get_daily_settlement_preview(branch_id: str = "HEADQUARTER", company: str = "tp_extra", admin_key: str = Depends(verify_admin_key)):
    today = datetime.now().date()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. ยอดขายแยกตามวิธีชำระ (เงินสด vs พร้อมเพย์)
            cursor.execute(
                """
                SELECT 
                    COUNT(id) as total_orders,
                    COALESCE(SUM(total_amount), 0) as gross_total,
                    COALESCE(SUM(CASE WHEN line_user_id = 'POS_CASH_CUSTOMER' THEN total_amount ELSE 0 END), 0) as cash_total,
                    COALESCE(SUM(CASE WHEN line_user_id != 'POS_CASH_CUSTOMER' THEN total_amount ELSE 0 END), 0) as promptpay_total
                FROM orders
                WHERE company_slug = %s AND status = 'paid' AND DATE(created_at) = %s;
                """,
                (company, today)
            )
            sales = cursor.fetchone()

            # 2. ยอดตัดแบ่ง 5 กองทุนของวันนี้
            cursor.execute(
                """
                SELECT 
                    COALESCE(SUM(supplier_cost_payable), 0) as supplier_pool,
                    COALESCE(SUM(branch_operating_share), 0) as branch_pool,
                    COALESCE(SUM(utility_reserve_accrual), 0) as utility_pool,
                    COALESCE(SUM(marketing_commission), 0) as commission_pool,
                    COALESCE(SUM(platform_net_gp), 0) as platform_gp
                FROM order_financial_splits
                WHERE company_slug = %s AND branch_id = %s AND DATE(created_at) = %s;
                """,
                (company, branch_id, today)
            )
            splits = cursor.fetchone()

            # 3. ผลต่างเงินสดจาก Blind Shift ล่าสุด
            cursor.execute(
                """
                SELECT COALESCE(SUM(variance_amount), 0) as total_variance
                FROM shift_cash_reconciliations
                WHERE company_slug = %s AND branch_id = %s AND shift_date = %s;
                """,
                (company, branch_id, today)
            )
            variance_row = cursor.fetchone()
            variance = float(variance_row["total_variance"]) if variance_row else 0.0

    return {
        "status": "success",
        "date": str(today),
        "branch_id": branch_id,
        "sales_summary": sales,
        "splits_summary": splits,
        "cash_variance": variance
    }

@router.post("/settlement/close-daily-ledger")
def close_daily_ledger(payload: CloseDailyLedgerRequest, admin_key: str = Depends(verify_admin_key)):
    today = datetime.now().date()
    preview = get_daily_settlement_preview(branch_id=payload.branch_id, company=payload.company_slug, admin_key=admin_key)
    sales = preview["sales_summary"]
    splits = preview["splits_summary"]

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_financial_closings (
                    closing_date, branch_id, company_slug,
                    total_orders_count, gross_sales_amount, cash_sales_amount, promptpay_sales_amount,
                    supplier_escrow_total, branch_operating_total, utility_reserve_total,
                    commission_total, platform_net_gp_total, cash_variance, closed_by_emp_code
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    total_orders_count = VALUES(total_orders_count),
                    gross_sales_amount = VALUES(gross_sales_amount),
                    cash_sales_amount = VALUES(cash_sales_amount),
                    promptpay_sales_amount = VALUES(promptpay_sales_amount),
                    supplier_escrow_total = VALUES(supplier_escrow_total),
                    branch_operating_total = VALUES(branch_operating_total),
                    utility_reserve_total = VALUES(utility_reserve_total),
                    commission_total = VALUES(commission_total),
                    platform_net_gp_total = VALUES(platform_net_gp_total),
                    cash_variance = VALUES(cash_variance);
                """,
                (
                    today, payload.branch_id, payload.company_slug,
                    sales["total_orders"], sales["gross_total"], sales["cash_total"], sales["promptpay_total"],
                    splits["supplier_pool"], splits["branch_pool"], splits["utility_pool"],
                    splits["commission_pool"], splits["platform_gp"], preview["cash_variance"],
                    payload.manager_emp_code
                )
            )
        conn.commit()

    return {
        "status": "success",
        "message": f"ปิดรอบบัญชีและล็อกยอดประจำวัน {today} สาขา {payload.branch_id} สำเร็จเรียบร้อย",
        "gross_sales": sales["gross_total"]
    }


from backend.app.services.tax_compliance_service import generate_monthly_tax_summary, export_etax_xml_template

@router.get("/tax/monthly-summary")
def get_tax_monthly_summary(
    year: int = Query(default=datetime.now().year),
    month: int = Query(default=datetime.now().month),
    company: str = Query(default="tp_extra"),
    admin_key: str = Depends(verify_admin_key)
):
    summary = generate_monthly_tax_summary(year, month, company_slug=company)
    return {"status": "success", "data": summary}

@router.get("/tax/export-etax-xml")
def download_etax_xml(order_no: str, admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT order_no, platform_net_gp, platform_vat_amount, company_slug
                FROM order_financial_splits
                WHERE order_no = %s;
                """,
                (order_no,)
            )
            row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลบิลสำหรับออกใบกำกับภาษี")

    xml_text = export_etax_xml_template(
        doc_number=f"TAX-{row['order_no']}",
        seller_tax_id="0105559998881",
        buyer_tax_id="0105500000000",
        amount=float(row["platform_net_gp"]),
        vat=float(row["platform_vat_amount"])
    )
    return Response(content=xml_text, media_type="application/xml")


class ToggleChecklistRequest(BaseModel):
    task_id: int
    checkpoint_index: int
    is_done: bool

class MarkTaskPaidRequest(BaseModel):
    task_id: int
    receipt_no: str
    amount_paid: float
    admin_emp_code: str = "CPA-ADMIN"

@router.get("/compliance/statutory-tasks")
def get_statutory_tasks(company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, authority_name, form_code, task_title, cycle_type,
                       DATE_FORMAT(due_date, '%d/%m/%Y') as due_date_formatted,
                       DATEDIFF(due_date, CURDATE()) as days_remaining,
                       base_amount, tax_or_fee_amount, payment_reference_no,
                       compliance_status, completed_at
                FROM statutory_compliance_tasks
                WHERE company_slug = %s
                ORDER BY due_date ASC;
                """,
                (company,)
            )
            tasks = cursor.fetchall()
    return {"status": "success", "tasks": tasks}

@router.post("/compliance/mark-task-paid")
def mark_task_submitted_and_paid(payload: MarkTaskPaidRequest, admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE statutory_compliance_tasks
                SET compliance_status = 'SUBMITTED_PAID',
                    payment_reference_no = %s,
                    tax_or_fee_amount = %s,
                    completed_by = %s,
                    completed_at = NOW()
                WHERE id = %s;
                """,
                (payload.receipt_no, payload.amount_paid, payload.admin_emp_code, payload.task_id)
            )
        conn.commit()

    return {
        "status": "success",
        "message": f"บันทึกผลการยื่นแบบและชำระเงินงานลำดับที่ {payload.task_id} สำเร็จเรียบร้อย (เลขที่ใบเสร็จ: {payload.receipt_no})"
    }


from backend.app.services.vendor_governance_service import scan_and_generate_vendor_alerts

class ResolveAlertRequest(BaseModel):
    alert_id: int
    resolved_by: str = "ADMIN_BUYER"

@router.get("/vendors/dashboard")
def get_vendor_governance_dashboard(company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    # สแกนความเสี่ยงอัตโนมัติก่อนส่งข้อมูล
    scan_and_generate_vendor_alerts(company_slug=company)

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. รายการแจ้งเตือนคู่ค้าที่ยังค้างอยู่
            cursor.execute(
                """
                SELECT id, supplier_code, alert_type, severity, alert_title, alert_detail,
                       DATE_FORMAT(due_date, '%d/%m/%Y') as due_date_formatted,
                       DATEDIFF(due_date, CURDATE()) as days_left
                FROM vendor_governance_alerts
                WHERE is_resolved = FALSE
                ORDER BY FIELD(severity, 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'), due_date ASC;
                """
            )
            alerts = cursor.fetchall()

            # 2. รายชื่อคู่ค้าทั้งหมดและสถานะความสอดคล้องทางกฎหมาย
            cursor.execute(
                """
                SELECT supplier_code, company_name, vendor_type, contact_person, contact_phone,
                       DATE_FORMAT(contract_end_date, '%d/%m/%Y') as contract_end_date,
                       DATEDIFF(contract_end_date, CURDATE()) as contract_days_left,
                       fda_license_no, performance_grade, compliance_status
                FROM vendor_compliance_profiles
                WHERE company_slug = %s
                ORDER BY contract_days_left ASC;
                """,
                (company,)
            )
            vendors = cursor.fetchall()

    return {
        "status": "success",
        "active_alerts_count": len(alerts),
        "alerts": alerts,
        "vendors": vendors
    }

@router.post("/vendors/resolve-alert")
def resolve_vendor_alert(payload: ResolveAlertRequest, admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendor_governance_alerts
                SET is_resolved = TRUE, resolved_by = %s, resolved_at = NOW()
                WHERE id = %s;
                """,
                (payload.resolved_by, payload.alert_id)
            )
        conn.commit()
    return {"status": "success", "message": f"ปิดรายการแจ้งเตือน {payload.alert_id} เรียบร้อย"}


from backend.app.services.vat_classifier import classify_product_tax

class ClassifyProductTaxRequest(BaseModel):
    product_name: str

@router.post("/tax/classify-product")
def api_classify_product_tax(payload: ClassifyProductTaxRequest, admin_key: str = Depends(verify_admin_key)):
    result = classify_product_tax(payload.product_name)
    return {"status": "success", "data": result}


from backend.app.services.shrinkage_maintenance_service import record_inventory_writeoff, record_asset_maintenance

class WriteOffRequest(BaseModel):
    sku: str
    quantity: int
    reason_type: str
    witness_emp: str
    manager_emp: str = "MGR-001"
    evidence_url: Optional[str] = None
    police_report: Optional[str] = None

class MaintenanceRequest(BaseModel):
    asset_name: str
    cost_amount: float
    vendor_name: str
    vendor_tax_id: str
    invoice_no: str
    authorized_by: str = "MGR-001"
    paid_from_fund: str = "BRANCH_UTILITY_RESERVE"

@router.post("/inventory/write-off")
def api_record_writeoff(payload: WriteOffRequest, admin_key: str = Depends(verify_admin_key)):
    try:
        res = record_inventory_writeoff(
            sku=payload.sku, quantity=payload.quantity, reason_type=payload.reason_type,
            witness_emp=payload.witness_emp, manager_emp=payload.manager_emp,
            evidence_url=payload.evidence_url, police_report=payload.police_report
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/assets/maintenance")
def api_record_maintenance(payload: MaintenanceRequest, admin_key: str = Depends(verify_admin_key)):
    res = record_asset_maintenance(
        asset_name=payload.asset_name, cost_amount=payload.cost_amount,
        vendor_name=payload.vendor_name, vendor_tax_id=payload.vendor_tax_id,
        invoice_no=payload.invoice_no, authorized_by=payload.authorized_by,
        paid_from_fund=payload.paid_from_fund
    )
    return res

@router.get("/shrinkage/summary")
def get_shrinkage_summary(company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, writeoff_no, sku, product_name, quantity, total_loss_value,
                       reason_type, tax_treatment, witness_emp_code, manager_authorizer,
                       DATE_FORMAT(created_at, '%d/%m/%Y %H:%i') as created_at
                FROM inventory_writeoffs
                WHERE company_slug = %s
                ORDER BY id DESC LIMIT 10;
                """,
                (company,)
            )
            writeoffs = cursor.fetchall()

            cursor.execute(
                """
                SELECT id, maint_no, asset_name, cost_amount, wht_deducted_3pct,
                       vendor_name, invoice_no, paid_from_fund,
                       DATE_FORMAT(created_at, '%d/%m/%Y') as created_at
                FROM asset_maintenance_logs
                WHERE company_slug = %s
                ORDER BY id DESC LIMIT 10;
                """,
                (company,)
            )
            maints = cursor.fetchall()

    return {"status": "success", "writeoffs": writeoffs, "maintenances": maints}


from backend.app.services.fefo_expiry_service import (
    receive_product_lot, generate_markdown_clearance_barcode, check_fefo_pos_item
)

class ReceiveLotRequest(BaseModel):
    sku: str
    lot_no: str
    mfg_date: str
    expiry_date: str
    quantity: int
    unit_cost: float
    selling_price: float
    ownership_type: str = "OWN_PURCHASE"
    supplier_code: str = "SUP-BP-001"

class CreateMarkdownRequest(BaseModel):
    lot_id: int
    discount_pct: float = 30.0

class PosItemCheckRequest(BaseModel):
    barcode_or_sku: str
    company_slug: str = "tp_extra"

@router.get("/inventory/lots")
def get_inventory_lots(company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT pl.id, pl.lot_no, pl.sku, p.name as product_name, pl.ownership_type,
                       pl.supplier_code, DATE_FORMAT(pl.mfg_date, '%d/%m/%Y') as mfg_date,
                       DATE_FORMAT(pl.expiry_date, '%d/%m/%Y') as expiry_date,
                       DATEDIFF(pl.expiry_date, CURDATE()) as days_to_expire,
                       pl.remaining_shelf_life_pct, pl.remaining_quantity,
                       pl.selling_price, pl.markdown_barcode, pl.markdown_discount_pct,
                       pl.markdown_price, pl.lot_status
                FROM product_lots pl
                JOIN products p ON pl.sku = p.sku AND p.company_slug = pl.company_slug
                WHERE pl.company_slug = %s AND pl.remaining_quantity > 0
                ORDER BY pl.expiry_date ASC;
                """,
                (company,)
            )
            lots = cursor.fetchall()
    return {"status": "success", "lots": lots}

@router.post("/inventory/receive-lot")
def api_receive_product_lot(payload: ReceiveLotRequest, admin_key: str = Depends(verify_admin_key)):
    try:
        res = receive_product_lot(
            sku=payload.sku, lot_no=payload.lot_no, mfg_date_str=payload.mfg_date,
            expiry_date_str=payload.expiry_date, quantity=payload.quantity,
            unit_cost=payload.unit_cost, selling_price=payload.selling_price,
            ownership_type=payload.ownership_type, supplier_code=payload.supplier_code
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/inventory/create-markdown")
def api_create_markdown(payload: CreateMarkdownRequest, admin_key: str = Depends(verify_admin_key)):
    try:
        res = generate_markdown_clearance_barcode(lot_id=payload.lot_id, discount_pct=payload.discount_pct)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/inventory/pos-check-item")
def api_pos_check_item(payload: PosItemCheckRequest):
    res = check_fefo_pos_item(barcode_or_sku=payload.barcode_or_sku, company_slug=payload.company_slug)
    return res


from backend.app.services.shelf_click_collect_service import (
    calculate_shelf_kpi_rankings, complete_customer_pickup, process_unclaimed_orders
)

class PickupScanRequest(BaseModel):
    pickup_code: str
    branch_id: str = "HEADQUARTER"
    company_slug: str = "tp_extra"

class PromoteShelfRequest(BaseModel):
    sku: str
    target_zone: str = "A2-MIDDLE"
    branch_id: str = "HEADQUARTER"
    company_slug: str = "tp_extra"

@router.get("/shelf/dashboard")
def get_shelf_dashboard(branch_id: str = "HEADQUARTER", company: str = "tp_extra", admin_key: str = Depends(verify_admin_key)):
    calculate_shelf_kpi_rankings(branch_id=branch_id, company_slug=company)

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. รายการสินค้าบนเชลฟ์และคะแนน KPI
            cursor.execute(
                """
                SELECT psp.*, p.name as product_name, p.price as price
                FROM product_shelf_placements psp
                JOIN products p ON psp.sku = p.sku AND p.company_slug = psp.company_slug
                WHERE psp.branch_id = %s AND psp.company_slug = %s
                ORDER BY psp.shelf_kpi_score DESC;
                """,
                (branch_id, company)
            )
            shelves = cursor.fetchall()

            # 2. รายการออเดอร์ Click & Collect รอรับที่สาขา
            cursor.execute(
                """
                SELECT id, order_no, customer_name, customer_phone, sku, quantity, total_amount,
                       DATE_FORMAT(arrived_at_branch_date, '%d/%m/%Y') as arrived_date,
                       DATE_FORMAT(pickup_deadline_date, '%d/%m/%Y') as deadline_date,
                       DATEDIFF(pickup_deadline_date, CURDATE()) as days_left,
                       pickup_status, pickup_qr_code, unclaimed_handling_fee
                FROM click_collect_orders
                WHERE pickup_branch_id = %s AND company_slug = %s
                ORDER BY FIELD(pickup_status, 'READY_FOR_PICKUP', 'UNCLAIMED_EXPIRED', 'COMPLETED_COLLECTED'), pickup_deadline_date ASC;
                """,
                (branch_id, company)
            )
            orders = cursor.fetchall()

    return {"status": "success", "shelves": shelves, "click_collect_orders": orders}

@router.post("/shelf/promote-to-physical")
def api_promote_shelf(payload: PromoteShelfRequest, admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE product_shelf_placements
                SET shelf_type = 'PHYSICAL_SHELF', shelf_zone = %s, qualification_status = 'REGULAR'
                WHERE sku = %s AND branch_id = %s AND company_slug = %s;
                """,
                (payload.target_zone, payload.sku, payload.branch_id, payload.company_slug)
            )
        conn.commit()
    return {"status": "success", "message": f"เลื่อนขั้นสินค้า {payload.sku} ขึ้นวางบนเชลฟ์จริงโซน {payload.target_zone} สำเร็จ"}

@router.post("/click-collect/scan-pickup")
def api_scan_pickup(payload: PickupScanRequest, admin_key: str = Depends(verify_admin_key)):
    try:
        res = complete_customer_pickup(
            pickup_qr_or_order=payload.pickup_code,
            branch_id=payload.branch_id,
            company_slug=payload.company_slug
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/click-collect/process-unclaimed")
def api_process_unclaimed(branch_id: str = "HEADQUARTER", company: str = "tp_extra", admin_key: str = Depends(verify_admin_key)):
    res = process_unclaimed_orders(branch_id=branch_id, company_slug=company)
    return res


from backend.app.services.stock_transfer_service import (
    create_stock_transfer_manifest, verify_and_receive_transfer
)

class CreateTransferRequest(BaseModel):
    origin_branch: str = "HEADQUARTER"
    destination_branch: str = "BRANCH-02"
    sku: str
    lot_no: str
    quantity: int
    sender_emp: str = "MGR-001"
    unit_weight: float = 150.0

class VerifyReceiveTransferRequest(BaseModel):
    transfer_no: str
    actual_weight_grams: float
    receiver_emp: str = "MGR-BRANCH02"

@router.get("/transfer/list")
def get_transfer_manifests(company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT st.id, st.transfer_no, st.origin_branch_id, st.destination_branch_id,
                       st.expected_weight_grams, st.actual_received_weight_grams,
                       st.weight_discrepancy_pct, st.sender_emp_code, st.receiver_emp_code,
                       st.transfer_status,
                       DATE_FORMAT(st.dispatched_at, '%d/%m/%Y %H:%i') as dispatched_at,
                       DATE_FORMAT(st.received_at, '%d/%m/%Y %H:%i') as received_at,
                       sti.sku, sti.lot_no, sti.quantity
                FROM stock_transfers st
                LEFT JOIN stock_transfer_items sti ON st.transfer_no = sti.transfer_no
                WHERE st.company_slug = %s
                ORDER BY st.id DESC LIMIT 15;
                """,
                (company,)
            )
            transfers = cursor.fetchall()
    return {"status": "success", "transfers": transfers}

@router.post("/transfer/dispatch")
def api_dispatch_transfer(payload: CreateTransferRequest, admin_key: str = Depends(verify_admin_key)):
    try:
        res = create_stock_transfer_manifest(
            origin_branch=payload.origin_branch,
            destination_branch=payload.destination_branch,
            sku=payload.sku, lot_no=payload.lot_no,
            quantity=payload.quantity, sender_emp=payload.sender_emp,
            unit_weight=payload.unit_weight
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/transfer/receive-verify")
def api_verify_receive_transfer(payload: VerifyReceiveTransferRequest, admin_key: str = Depends(verify_admin_key)):
    try:
        res = verify_and_receive_transfer(
            transfer_no=payload.transfer_no,
            actual_weight_grams=payload.actual_weight_grams,
            receiver_emp=payload.receiver_emp
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


from backend.app.services.cycle_count_service import (
    get_blind_count_sheet, process_blind_count_submission
)

class BlindCountSubmitRequest(BaseModel):
    branch_id: str = "HEADQUARTER"
    company_slug: str = "tp_extra"
    counter_emp: str
    witness_emp: str
    records: list

@router.get("/audit/blind-sheet")
def api_get_blind_sheet(branch_id: str = "HEADQUARTER", company: str = "tp_extra", admin_key: str = Depends(verify_admin_key)):
    sheet = get_blind_count_sheet(branch_id=branch_id, company_slug=company)
    return sheet

@router.post("/audit/submit-blind-count")
def api_submit_blind_count(payload: BlindCountSubmitRequest, admin_key: str = Depends(verify_admin_key)):
    try:
        res = process_blind_count_submission(
            counted_records=payload.records,
            counter_emp=payload.counter_emp,
            witness_emp=payload.witness_emp,
            branch_id=payload.branch_id,
            company_slug=payload.company_slug
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/audit/history")
def get_audit_history(company: str = Query(default="tp_extra"), admin_key: str = Depends(verify_admin_key)):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT audit_no, branch_id, DATE_FORMAT(audit_date, '%d/%m/%Y') as audit_date,
                       counter_emp_code, witness_emp_code, total_items_audited,
                       matched_items_count, discrepant_items_count, net_variance_value,
                       accuracy_rate_pct, audit_status,
                       DATE_FORMAT(manager_signed_at, '%d/%m/%Y %H:%i') as signed_at
                FROM inventory_cycle_audits
                WHERE company_slug = %s
                ORDER BY id DESC LIMIT 10;
                """,
                (company,)
            )
            audits = cursor.fetchall()
    return {"status": "success", "audits": audits}
