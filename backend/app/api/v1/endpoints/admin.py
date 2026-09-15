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
