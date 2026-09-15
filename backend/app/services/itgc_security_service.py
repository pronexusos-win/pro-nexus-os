import hashlib
import json
from datetime import datetime
from backend.app.core.database import get_db_connection

def calculate_audit_hash(previous_hash: str, payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True)
    raw = f"{previous_hash}|{serialized}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def record_audit_chain_entry(module: str, ref_no: str, action: str, actor: str, payload: dict):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # ดึง Hash ล่าสุดของโมดูลนี้
            cursor.execute("""
                SELECT current_payload_hash FROM system_audit_chains
                WHERE module_name = %s ORDER BY id DESC LIMIT 1;
            """, (module,))
            last_row = cursor.fetchone()
            prev_hash = last_row["current_payload_hash"] if last_row else "GENESIS_HASH_BLOCK_2026"

            curr_hash = calculate_audit_hash(prev_hash, payload)

            cursor.execute("""
                INSERT INTO system_audit_chains (
                    module_name, record_ref_no, action_type, actor_emp_code,
                    previous_hash, current_payload_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (module, ref_no, action, actor, prev_hash, curr_hash))
        conn.commit()

    return curr_hash

def request_dual_key_authorization(desc: str, module: str, ref_id: str, requester: str, risk: str = "HIGH"):
    ticket_no = f"DK-{datetime.now().strftime('%Y%m%d%H%M')}"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO dual_key_authorizations (
                    auth_ticket_no, action_description, risk_level, target_module,
                    target_ref_id, first_key_emp, auth_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'PENDING_SECOND_KEY');
            """, (ticket_no, desc, risk, module, ref_id, requester))
        conn.commit()
    return ticket_no
