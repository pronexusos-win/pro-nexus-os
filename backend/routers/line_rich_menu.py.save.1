import requests
import os
from fastapi import APIRouter, HTTPException
from core.database import get_db_connection

router = APIRouter()

LINE_TOKENS = {
    "tp": os.getenv("LINE_TOKEN_TP", "token_tp_extra_12345"),
    "luckio": os.getenv("LINE_TOKEN_LUCKIO", "token_luckio_67890")
}

@router.post("/set-brand-rich-menu/{member_id}")
def assign_brand_rich_menu(member_id: str, brand: str):
    if brand not in LINE_TOKENS:
        raise HTTPException(status_code=400, detail="ไม่พบแบรนด์นี้ในระบบ")
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT role, line_user_id FROM members WHERE member_id = %s", (member_id,))
            user = cursor.fetchone()
            
            if not user or not user['line_user_id']:
                return {"status": "error", "message": "ไม่พบข้อมูลสมาชิกหรือยังไม่ได้ผูก LINE"}
                
            role = user['role']
            line_user_id = user['line_user_id']
            
            rich_menu_matrix = {
                "tp": {
                    "customer": "richmenu-tp-customer-xxxx",
                    "merchant": "richmenu-tp-merchant-xxxx",
                    "admin": "richmenu-tp-admin-xxxx"
                },
                "luckio": {
                    "customer": "richmenu-luckio-customer-yyyy",
                    "merchant": "richmenu-luckio-merchant-yyyy",
                    "admin": "richmenu-luckio-admin-yyyy"
                }
            }
            
            target_menu_id = rich_menu_matrix.get(brand, {}).get(role)
            if not target_menu_id:
                return {"status": "error", "message": "ไม่พบการตั้งค่า Rich Menu สำหรับเงื่อนไขนี้"}
            
            headers = {
                "Authorization": f"Bearer {LINE_TOKENS[brand]}",
                "Content-Type": "application/json"
            }
            url = f"https://api.line.me/v2/bot/user/{line_user_id}/richmenu/{target_menu_id}"
            response = requests.post(url, headers=headers)
            
            return {
                "status": "success",
                "brand": brand,
                "role": role,
                "assigned_rich_menu": target_menu_id,
                "line_api_status": response.status_code
            }
    finally:
        conn.close()
