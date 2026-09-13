from core.database import get_db_connection
import json

def setup_configs():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # เพิ่มคอลัมน์สำหรับเก็บการตั้งค่าแบบยืดหยุ่น (JSON)
            try:
                cursor.execute("ALTER TABLE tenants ADD COLUMN branding JSON")
                cursor.execute("ALTER TABLE tenants ADD COLUMN modules JSON")
            except Exception as e:
                pass # กรณีคอลัมน์มีอยู่แล้วจะข้ามไป
            
            # ตั้งค่าเริ่มต้น: เปิดทุกฟีเจอร์ให้ทุกบริษัท
            default_modules = json.dumps({
                "unilevel": True, 
                "cashback": True, 
                "company_fund": True
            })
            default_branding = json.dumps({
                "theme_color": "#1890ff", 
                "logo_url": "https://default-logo.com/logo.png",
                "company_name_th": "บริษัท ค่าเริ่มต้น จำกัด"
            })
            
            cursor.execute("""
                UPDATE tenants 
                SET modules = COALESCE(modules, %s), 
                    branding = COALESCE(branding, %s)
            """, (default_modules, default_branding))
            
        conn.commit()
        print("✅ Tenant Configurations (Branding & Modules) updated successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_configs()
