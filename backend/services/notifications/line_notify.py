def send_line_notification(message: str, line_user_id: str = None):
    # ในระบบจริงจะใช้ LINE Messaging API / LINE Notify SDK ยิงไปที่ Server ของ LINE
    # สำหรับตอนนี้เราทำระบบ Mock (จำลอง) ให้ Print ออกมาที่ Log ของ Docker ก่อน
    print(f"\n[🟢 LINE MOCK MESSAGE] ➡️ To User ID: {line_user_id}")
    print(f"💬 ข้อความ: {message}\n")
    return True
