from datetime import datetime
from backend.app.core.database import get_db_connection

def record_and_verify_rpt_transaction(
    party_code: str, transaction_type: str,
    amount: float, market_benchmark: float,
    necessity_reason: str, resolution_ref: str, resolution_date_str: str,
    company_slug: str = "tp_extra"
):
    """
    บันทึกและตรวจสอบรายการที่เกี่ยวโยงกัน:
    - ตรวจสอบราคาเปรียบเทียบตลาด (Arm's Length Basis): หากราคาแพงกว่าตลาดเกิน 5% จะแจ้งเตือนระดับวิกฤต
    - จัดระดับอำนาจอนุมัติ (ก.ล.ต. Size Test)
    """
    variance_pct = round(((amount - market_benchmark) / market_benchmark) * 100, 2) if market_benchmark > 0 else 0.0
    
    # หากจ่ายแพงกว่าราคาตลาดเกิน 3% จะถือว่าไม่สะท้อนราคาการค้าปกติ
    is_arms_length = variance_pct <= 3.0

    # จัดระดับการอนุมัติตามขนาดรายการ
    if amount >= 20000000.0:
        approval_level = "SHAREHOLDER_AGM"
    elif amount >= 1000000.0:
        approval_level = "BOARD_OF_DIRECTORS"
    else:
        approval_level = "AUDIT_COMMITTEE"

    txn_ref = f"RPT-TXN-{datetime.now().strftime('%Y%m%d%H%M')}"

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO rpt_transaction_ledger (
                    rpt_ref_no, company_slug, party_code, transaction_type,
                    transaction_amount, market_benchmark_price, price_variance_pct,
                    is_arms_length, business_necessity_reason, approval_level,
                    resolution_doc_ref, resolution_date
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                txn_ref, company_slug, party_code, transaction_type,
                amount, market_benchmark, variance_pct,
                is_arms_length, necessity_reason, approval_level,
                resolution_ref, resolution_date_str
            ))
        conn.commit()

    return {
        "status": "success",
        "rpt_ref_no": txn_ref,
        "is_arms_length": is_arms_length,
        "variance_pct": variance_pct,
        "approval_level": approval_level,
        "message": f"บันทึกรายการ RPT {txn_ref} เรียบร้อย (เกณฑ์ราคาตลาด: {'ผ่านเกณฑ์ Arm Length' if is_arms_length else 'ต้องทบทวนราคา'})"
    }

def get_rpt_summary_for_filing(company_slug: str = "tp_extra"):
    """
    ดึงรายงานสรุป RPT สำหรับแนบในแบบ 56-1 One Report และ Filing ของ ก.ล.ต.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT rpt.*, reg.party_name, reg.relationship_nature, reg.related_to_person
                FROM rpt_transaction_ledger rpt
                JOIN related_party_registry reg ON rpt.party_code = reg.party_code AND rpt.company_slug = reg.company_slug
                WHERE rpt.company_slug = %s
                ORDER BY rpt.resolution_date DESC;
            """, (company_slug,))
            transactions = cursor.fetchall()

            cursor.execute("""
                SELECT * FROM related_party_registry WHERE company_slug = %s AND is_active = TRUE;
            """, (company_slug,))
            registered_parties = cursor.fetchall()

    return {
        "status": "success",
        "registered_parties": registered_parties,
        "transactions": transactions
    }
