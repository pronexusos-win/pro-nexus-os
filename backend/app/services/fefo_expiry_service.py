from datetime import datetime, date
from backend.app.core.database import get_db_connection

def receive_product_lot(
    sku: str, lot_no: str, mfg_date_str: str, expiry_date_str: str,
    quantity: int, unit_cost: float, selling_price: float,
    ownership_type: str = "OWN_PURCHASE", supplier_code: str = "SUP-BP-001",
    branch_id: str = "HEADQUARTER", company_slug: str = "tp_extra"
):
    """
    ด่านตรวจรับสินค้าเข้าคลัง (Goods Receipt with Remaining Shelf Life Validation)
    """
    mfg = datetime.strptime(mfg_date_str, "%Y-%m-%d").date()
    exp = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
    today = date.today()

    if exp <= today:
        raise ValueError("ปฏิเสธการรับเข้า: สินค้าหมดอายุแล้ว ไม่สามารถรับเข้าคลังได้")

    total_days = (exp - mfg).days
    remaining_days = (exp - today).days
    rsl_pct = round((remaining_days / total_days) * 100, 2) if total_days > 0 else 0

    # กฎ RSL ขั้นต่ำ (อาหาร 70%, สกินแคร์/เครื่องสำอาง 75%)
    min_required_rsl = 70.0
    if "SKIN" in sku or "COSMETIC" in sku:
        min_required_rsl = 75.0

    if rsl_pct < min_required_rsl:
        raise ValueError(
            f"❌ ปฏิเสธการรับเข้า (RSL ต่ำกว่าเกณฑ์): สินค้ามีอายุคงเหลือเพียง {rsl_pct}% "
            f"ซึ่งต่ำกว่ามาตรฐานขั้นต่ำที่กำหนด ({min_required_rsl}%) ต้องส่งคืนซัพพลายเออร์ทันที"
        )

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO product_lots (
                    lot_no, sku, company_slug, branch_id, ownership_type, supplier_code,
                    mfg_date, expiry_date, received_date, total_shelf_life_days, remaining_shelf_life_pct,
                    received_quantity, remaining_quantity, unit_cost, selling_price, lot_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'NORMAL')
                ON DUPLICATE KEY UPDATE
                    received_quantity = received_quantity + VALUES(received_quantity),
                    remaining_quantity = remaining_quantity + VALUES(remaining_quantity);
            """, (
                lot_no, sku, company_slug, branch_id, ownership_type, supplier_code,
                mfg, exp, today, total_days, rsl_pct,
                quantity, quantity, unit_cost, selling_price
            ))

            # อัปเดตสต็อกรวมในตารางสินค้าหลัก
            cursor.execute("""
                UPDATE products 
                SET stock_quantity = stock_quantity + %s
                WHERE sku = %s AND company_slug = %s;
            """, (quantity, sku, company_slug))

        conn.commit()

    return {
        "status": "success",
        "lot_no": lot_no,
        "sku": sku,
        "quantity_received": quantity,
        "remaining_shelf_life_pct": rsl_pct,
        "message": f"ตรวจรับสินค้าล็อต {lot_no} สำเร็จ อายุคงเหลือสมบูรณ์ ({rsl_pct}%)"
    }

def generate_markdown_clearance_barcode(lot_id: int, discount_pct: float = 30.0):
    """
    ออกบาร์โค้ดป้ายเหลืองลดราคาเฉพาะชิ้น (Dynamic Markdown Clearance)
    เช่น Prefix '290-' เพื่อให้ POS แยกคิดราคาสินค้าใกล้หมดอายุได้อย่างถูกต้อง
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM product_lots WHERE id = %s;", (lot_id,))
            lot = cursor.fetchone()
            if not lot:
                raise ValueError("ไม่พบล็อตสินค้า")

            normal_price = float(lot["selling_price"])
            discount_multiplier = (100.0 - discount_pct) / 100.0
            markdown_price = round(normal_price * discount_multiplier, 2)
            
            # รหัสบาร์โค้ดป้ายเหลืองมาตรฐานค้าปลีก (Prefix 290)
            markdown_barcode = f"290-{lot['sku']}-DISC{int(discount_pct)}"

            cursor.execute("""
                UPDATE product_lots
                SET markdown_barcode = %s,
                    markdown_discount_pct = %s,
                    markdown_price = %s,
                    lot_status = 'CLEARANCE_ACTIVE'
                WHERE id = %s;
            """, (markdown_barcode, discount_pct, markdown_price, lot_id))
        conn.commit()

    return {
        "status": "success",
        "lot_no": lot["lot_no"],
        "markdown_barcode": markdown_barcode,
        "discount_pct": discount_pct,
        "normal_price": normal_price,
        "markdown_price": markdown_price
    }

def check_fefo_pos_item(barcode_or_sku: str, company_slug: str = "tp_extra"):
    """
    ฟังก์ชันตรวจสอบความปลอดภัยก่อนคิดเงินบน POS (POS Expiry & Barcode Shield):
    1. ถ้าเป็นบาร์โค้ดป้ายเหลือง (Prefix 290-) -> ดึงราคาลดพิเศษและตัดล็อตนั้น
    2. ตรวจสอบวันหมดอายุ ถ้าเหลือน้อยกว่าหรือเท่ากับ 7 วัน -> บล็อกไม่ให้ขาย (Quarantined)
    3. แนะนำล็อตที่ต้องหยิบขายตามหลัก FEFO
    """
    today = date.today()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # กรณีที่ 1: สแกนบาร์โค้ดป้ายเหลือง
            cursor.execute("""
                SELECT pl.*, p.name as product_name
                FROM product_lots pl
                JOIN products p ON pl.sku = p.sku AND p.company_slug = pl.company_slug
                WHERE pl.markdown_barcode = %s AND pl.company_slug = %s AND pl.remaining_quantity > 0;
            """, (barcode_or_sku, company_slug))
            markdown_item = cursor.fetchone()

            if markdown_item:
                days_left = (markdown_item["expiry_date"] - today).days
                if days_left <= 7:
                    return {
                        "is_allowed": False,
                        "block_reason": f"🚨 ปฏิเสธการขาย: สินค้าล็อต {markdown_item['lot_no']} เหลืออายุเพียง {days_left} วัน (ต่ำกว่าเกณฑ์ความปลอดภัย 7 วัน) ต้องกักกันส่งทำลายตามระเบียบ อย. และ ป.79"
                    }
                return {
                    "is_allowed": True,
                    "is_markdown": True,
                    "sku": markdown_item["sku"],
                    "product_name": f"{markdown_item['product_name']} (ป้ายเหลืองลด {int(markdown_item['markdown_discount_pct'])}%)",
                    "price": float(markdown_item["markdown_price"]),
                    "lot_no": markdown_item["lot_no"],
                    "expiry_date": str(markdown_item["expiry_date"]),
                    "days_left": days_left
                }

            # กรณีที่ 2: สแกนบาร์โค้ดปกติของสินค้า ให้หาล็อตที่หมดอายุก่อนสุด (FEFO)
            cursor.execute("""
                SELECT pl.*, p.name as product_name
                FROM product_lots pl
                JOIN products p ON pl.sku = p.sku AND p.company_slug = pl.company_slug
                WHERE (pl.sku = %s OR p.sku = %s) AND pl.company_slug = %s AND pl.remaining_quantity > 0
                ORDER BY pl.expiry_date ASC LIMIT 1;
            """, (barcode_or_sku, barcode_or_sku, company_slug))
            fefo_lot = cursor.fetchone()

            if not fefo_lot:
                # ถ้าไม่เจอล็อต ให้ค้นจากตารางสินค้าหลักตามปกติ
                cursor.execute("SELECT * FROM products WHERE sku = %s AND company_slug = %s;", (barcode_or_sku, company_slug))
                prod = cursor.fetchone()
                if not prod:
                    return {"is_allowed": False, "block_reason": "ไม่พบรหัสสินค้า"}
                return {
                    "is_allowed": True,
                    "is_markdown": False,
                    "sku": prod["sku"],
                    "product_name": prod["name"],
                    "price": float(prod["price"]),
                    "lot_no": "GENERAL-STOCK",
                    "expiry_date": "-",
                    "days_left": 999
                }

            days_left = (fefo_lot["expiry_date"] - today).days
            if days_left <= 7:
                return {
                    "is_allowed": False,
                    "block_reason": f"🚨 ระบบล็อกการขาย: ล็อตเก่าสุดบนเชลฟ์ ({fefo_lot['lot_no']}) เหลืออายุ {days_left} วัน ห้ามจำหน่ายเด็ดขาด กรุณาปลดลงจากเชลฟ์เพื่อทำลาย"
                }

            return {
                "is_allowed": True,
                "is_markdown": False,
                "sku": fefo_lot["sku"],
                "product_name": fefo_lot["product_name"],
                "price": float(fefo_lot["selling_price"]),
                "lot_no": fefo_lot["lot_no"],
                "expiry_date": str(fefo_lot["expiry_date"]),
                "days_left": days_left,
                "fefo_instruction": f"💡 ตรวจสอบเชลฟ์: กรุณาหยิบจากล็อต {fefo_lot['lot_no']} (หมดอายุ {fefo_lot['expiry_date']}) ที่วางอยู่แถวหน้าสุด"
            }
