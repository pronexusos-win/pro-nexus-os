from fastapi import APIRouter, Depends
from middleware.tenant import verify_tenant_header
import base64

router = APIRouter()

@router.get("/generate-basket-link")
def generate_basket_link(product_id: str, member_id: str, tenant_id: str = Depends(verify_tenant_header)):
    # เข้ารหัสข้อมูลสร้างเป็นลิงก์สั้นๆ ป้องกันคนแก้ไขรหัสผู้แนะนำ
    raw_data = f"{tenant_id}:{member_id}:{product_id}"
    ref_code = base64.urlsafe_b64encode(raw_data.encode()).decode().rstrip("=")
    
    # ลิงก์สำหรับเอาไปแปะปักตะกร้าใน TikTok / Facebook / LINE
    basket_url = f"https://shop.pronexusos.com/buy/{ref_code}"
    
    return {
        "status": "success",
        "message": "สร้างลิงก์ปักตะกร้าเรียบร้อย",
        "basket_url": basket_url,
        "ref_code": ref_code
    }
