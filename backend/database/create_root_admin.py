from core.database import get_db_connection
import bcrypt

def create_root():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ตั้งรหัสผ่านเริ่มต้น (เปลี่ยนทีหลังได้)
            raw_password = "godmode_2026!"
            hashed_pw = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # เสกบัญชี Super Admin ของ TP Extra
            cursor.execute("""
                INSERT IGNORE INTO users (user_id, tenant_id, first_name, last_name, phone, role, password_hash) 
                VALUES 
                ('ADMIN-001', 'tp_extra', 'Super', 'Admin', '0800000000', 'SUPER_ADMIN', %s)
            """, (hashed_pw,))
            
        conn.commit()
        print(f"✅ เสกบัญชี Super Admin สำเร็จ!\nเบอร์โทร (User): 0800000000\nรหัสผ่าน: {raw_password}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_root()
