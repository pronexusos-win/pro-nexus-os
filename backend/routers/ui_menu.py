from fastapi import APIRouter, Depends
from middleware.tenant import verify_tenant_header

router = APIRouter()

@router.get("/dynamic-menu")
def get_dynamic_menu(role: str = "member", tenant_id: str = Depends(verify_tenant_header)):
    # โครงสร้างเมนูพื้นฐานที่ทุกคนเห็น
    menus = [
        {"id": "shop", "title": "สั่งซื้อสินค้า", "icon": "cart", "action": "open_liff_shop"},
        {"id": "wallet", "title": "กระเป๋าเงิน 80/20", "icon": "wallet", "action": "open_liff_wallet"}
    ]
    
    # เพิ่มเมนูตาม Role
    if role in ["super_admin", "company_admin"]:
        menus.append({"id": "admin_dash", "title": "หลังบ้านผู้บริหาร", "icon": "chart", "action": "open_admin_panel"})
        
    # เพิ่มเมนูตาม Tenant (บริษัท)
    if tenant_id == "tenant_peak_icon":
        menus.append({"id": "logistics", "title": "เช็คสถานะพัสดุ", "icon": "box", "action": "open_liff_tracking"})
    elif tenant_id == "tenant_tp_extra":
        menus.append({"id": "team", "title": "สายงาน Affiliate", "icon": "users", "action": "open_liff_team"})

    return {"status": "success", "tenant_id": tenant_id, "role": role, "allowed_menus": menus}
