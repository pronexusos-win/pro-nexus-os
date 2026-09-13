from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from core.database import get_db_connection
import os

router = APIRouter()

# กำหนดค่า OAuth (ดึงจาก Environment Variables หรือกำหนดค่าจำลองสำหรับใช้งานจริง)
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID', 'mock_google_client_id'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET', 'mock_google_client_secret'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@router.get('/login')
async def login_via_google(request: Request):
    # ในการใช้งานจริง หน้านี้จะเด้งไปหน้าเลือกบัญชี Google ของผู้ใช้งาน
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/callback')
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="ไม่สามารถดึงข้อมูลผู้ใช้จาก Google ได้")
            
        email = user_info['email']
        name = user_info['name']
        google_id = user_info['sub']
        
        # เช็คในฐานข้อมูลว่ามีอีเมลนี้หรือยัง ถ้ายังให้สร้างบัญชีอัตโนมัติหรือผูกสิทธิ์
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT member_id, role, tenant_id FROM members WHERE email = %s", (email,))
                member = cursor.fetchone()
                
                if not member:
                    # กรณีสมัครสมาชิกใหม่ผ่าน Google (กำหนดสิทธิ์เบื้องต้นเป็น staff หรือ member)
                    # ในระบบจริงสามารถให้ Super Admin อัปเกรดสิทธิ์ทีหลังได้
                    pass
        finally:
            conn.close()
            
        # ส่งข้อมูลสำเร็จ (หรือ Redirect ไปหน้าแดชบอร์ดหลังบ้าน)
        return {
            "status": "success",
            "message": f"ยินดีต้อนรับคุณ {name} เข้าสู่ระบบ Pro Nexus OS",
            "google_email": email,
            "google_id": google_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"การยืนยันตัวตนล้มเหลว: {str(e)}")
