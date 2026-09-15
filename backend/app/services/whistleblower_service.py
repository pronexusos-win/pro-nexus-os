import secrets
import string
from datetime import datetime
from backend.app.core.database import get_db_connection

def generate_random_passcode(length=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def submit_whistleblower_report(
    category: str, location: str, title: str, description: str,
    evidence_url: str = None, is_anonymous: bool = True,
    contact_info: str = None, company_slug: str = "tp_extra"
):
    """
    รับเรื่องร้องเรียนและสร้างรหัสติดตามลับ (Anonymous Whistleblowing Entry)
    """
    case_token = f"WBL-{datetime.now().strftime('%Y%m')}-{secrets.token_hex(2).upper()}"
    passcode = generate_random_passcode(8)

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO whistleblower_cases (
                    case_token, tracking_passcode, company_slug, category,
                    incident_location, subject_title, description, evidence_url,
                    is_anonymous, whistleblower_contact, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING_REVIEW');
            """, (
                case_token, passcode, company_slug, category,
                location, title, description, evidence_url,
                is_anonymous, contact_info
            ))
        conn.commit()

    return {
        "status": "success",
        "case_token": case_token,
        "tracking_passcode": passcode,
        "message": "ส่งเบาะแสการทุจริตเข้าสู่คณะกรรมการตรวจสอบเรียบร้อย กรุณาเก็บรหัสติดตามไว้เพื่อตรวจสอบความคืบหน้า"
    }

def track_case_progress(case_token: str, passcode: str, company_slug: str = "tp_extra"):
    """
    ตรวจสอบความคืบหน้าของคดีโดยผู้แจ้งเบาะแส
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT case_token, category, incident_location, subject_title, status,
                       audit_committee_notes, created_at, resolved_at
                FROM whistleblower_cases
                WHERE case_token = %s AND tracking_passcode = %s AND company_slug = %s;
            """, (case_token, passcode, company_slug))
            case = cursor.fetchone()

    if not case:
        raise ValueError("ไม่พบคดี หรือรหัสผ่านติดตามไม่ถูกต้อง")

    return {
        "status": "success",
        "case": case
    }
