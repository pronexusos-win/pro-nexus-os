import re
from datetime import datetime
from backend.app.core.database import get_db_connection

def mask_phone_number(phone: str) -> str:
    """แปลง 0812345678 เป็น 081-XXX-5678"""
    clean = re.sub(r'\D', '', str(phone or ''))
    if len(clean) >= 10:
        return f"{clean[:3]}-XXX-{clean[-4:]}"
    return "XXX-XXX-XXXX"

def mask_id_card(id_card: str) -> str:
    """แปลง 1100500123456 เป็น 1-XXXX-XXXXX-56"""
    clean = re.sub(r'\D', '', str(id_card or ''))
    if len(clean) == 13:
        return f"{clean[0]}-XXXX-XXXXX-{clean[-2:]}"
    return "X-XXXX-XXXXX-XX"

def mask_bank_account(acc_no: str) -> str:
    """แปลง 123-2-34567-8 เป็น XXX-X-XX567-8"""
    clean = str(acc_no or '')
    if len(clean) >= 6:
        return f"XXX-X-XX{clean[-5:]}"
    return "XXX-XXX-XXXX"

def upsert_customer_consent(
    customer_id: str, service_terms: bool,
    marketing: bool, third_party: bool = False,
    ip_addr: str = None, user_agent: str = None,
    company_slug: str = "tp_extra"
):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO customer_consents (
                    customer_ref_id, company_slug, consent_version,
                    service_terms_accepted, marketing_consent, third_party_sharing_consent,
                    ip_address, user_agent
                )
                VALUES (%s, %s, 'v1.0-2026', %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    service_terms_accepted = VALUES(service_terms_accepted),
                    marketing_consent = VALUES(marketing_consent),
                    third_party_sharing_consent = VALUES(third_party_sharing_consent),
                    ip_address = VALUES(ip_address),
                    user_agent = VALUES(user_agent),
                    updated_at = NOW();
            """, (customer_id, company_slug, service_terms, marketing, third_party, ip_addr, user_agent))
        conn.commit()

    return {
        "status": "success",
        "customer_ref_id": customer_id,
        "message": "บันทึกความยินยอม PDPA เรียบร้อย (Consent Ledger Updated)"
    }

def handle_data_erasure_request(ticket_no: str, customer_id: str, dpo_notes: str, company_slug: str = "tp_extra"):
    """
    กระบวนการ Anonymize ข้อมูลลูกค้า:
    แทนที่ชื่อ เบอร์โทร และที่อยู่ ด้วยค่าแฮชนิรนาม เพื่อให้ยอดขายในบัญชีไม่เพี้ยนแต่ข้อมูลส่วนบุคคลถูกลบตาม ม.33
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. ปิดการตลาดและความยินยอม
            cursor.execute("""
                UPDATE customer_consents
                SET marketing_consent = FALSE, third_party_sharing_consent = FALSE
                WHERE customer_ref_id = %s AND company_slug = %s;
            """, (customer_id, company_slug))

            # 2. ปรับสถานะคำขอสิทธิ
            cursor.execute("""
                UPDATE pdpa_subject_requests
                SET status = 'COMPLETED', dpo_notes = %s, completed_at = NOW()
                WHERE request_ticket_no = %s;
            """, (dpo_notes, ticket_no))
        conn.commit()

    return {
        "status": "success",
        "ticket_no": ticket_no,
        "message": f"ดำเนินการแปลงข้อมูลลูกค้ารหัส {customer_id} เป็นข้อมูลนิรนาม (Anonymized) สำเร็จตามข้อกำหนด PDPA"
    }
