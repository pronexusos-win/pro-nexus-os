import secrets
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.core.database import get_db_connection

router = APIRouter(prefix="/scanner-auth", tags=["Scanner Multi-Company Auth"])

class InitSessionPayload(BaseModel):
    company_slug: str = "pro_nexus"

class ConfirmAuthPayload(BaseModel):
    session_token: str
    line_user_id: str
    display_name: str

@router.post("/create-session")
def create_web_session(payload: InitSessionPayload):
    token = secrets.token_hex(24)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO web_login_sessions (session_token, company_slug, status)
                VALUES (%s, %s, 'WAITING_SCAN');
            """, (token, payload.company_slug))
        conn.commit()
    return {"status": "success", "session_token": token, "company_slug": payload.company_slug}

@router.get("/check-session/{session_token}")
def check_session_status(session_token: str):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT session_token, company_slug, line_user_id, display_name, status
                FROM web_login_sessions WHERE session_token = %s;
            """, (session_token,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="ไม่พบ Session นี้")
    return {"status": row["status"], "company_slug": row["company_slug"], "user": row}

@router.post("/confirm-auth")
def confirm_line_auth(payload: ConfirmAuthPayload):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE web_login_sessions
                SET line_user_id = %s,
                    display_name = %s,
                    status = 'AUTHENTICATED',
                    authenticated_at = NOW()
                WHERE session_token = %s AND status = 'WAITING_SCAN';
            """, (payload.line_user_id, payload.display_name, payload.session_token))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=400, detail="Token หมดอายุหรือถูกยืนยันไปแล้ว")
        conn.commit()
    return {"status": "success", "message": "ยืนยันสิทธิ์ LINE สำเร็จ"}
