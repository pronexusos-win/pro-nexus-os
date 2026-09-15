import requests

# Channel Access Token จาก LINE Developers Console ของ LINE OA นั้นๆ
CHANNEL_ACCESS_TOKEN = "YOUR_LINE_CHANNEL_ACCESS_TOKEN"

def link_rich_menu_to_user(line_user_id: str, rich_menu_id: str):
    """
    ผูกริชเมนูเฉพาะบุคคล (เช่น สลับเป็นเมนูพนักงาน / แคชเชียร์)
    """
    url = f"https://api.line.me/v2/bot/user/{line_user_id}/richmenu/{rich_menu_id}"
    headers = {"Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    res = requests.post(url, headers=headers)
    return res.status_code == 200

def unlink_rich_menu_from_user(line_user_id: str):
    """
    ปลดริชเมนูเฉพาะบุคคล ให้กลับไปใช้ริชเมนูลูกค้าทั่วไป (Default Menu)
    """
    url = f"https://api.line.me/v2/bot/user/{line_user_id}/richmenu"
    headers = {"Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    res = requests.delete(url, headers=headers)
    return res.status_code == 200
