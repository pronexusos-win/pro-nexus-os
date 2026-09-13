from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import serial
import socket
# from escpos.printer import Network, Usb # ใช้ในระบบจริงที่ต่อกับพรินเตอร์

router = APIRouter()

class PrinterConfig(BaseModel):
    ip_address: str = "192.168.1.100" # สำหรับ Network Printer
    port: int = 9100

class ScaleConfig(BaseModel):
    com_port: str = "COM3" # หรือ /dev/ttyUSB0 สำหรับ Linux/Mac
    baudrate: int = 9600

@router.post("/hardware/drawer/kick")
def kick_cash_drawer(config: PrinterConfig):
    """
    (8.3) ระบบเตะลิ้นชักเงินอัตโนมัติ 
    ทำงานโดยการส่งคำสั่ง ESC/POS (Pulse command) ไปที่เครื่องพิมพ์สลิป (Thermal Printer)
    ซึ่งลิ้นชักจะต่อสาย RJ11 อยู่กับเครื่องพิมพ์
    """
    try:
        # คำสั่ง ESC/POS มาตรฐานสำหรับเตะลิ้นชัก (Pulse 1, 50ms on, 50ms off)
        kick_command = b'\x27\x70\x00\x19\xfa'
        
        # ส่งคำสั่งผ่าน Network (LAN/Wi-Fi Printer)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((config.ip_address, config.port))
            s.sendall(kick_command)
            
        return {"status": "success", "message": "ลิ้นชักเงินเปิดแล้ว!"}
    except Exception as e:
        print(f"Hardware Error: {e}")
        # สำหรับโหมดทดสอบ ถ้าไม่ได้ต่อพรินเตอร์จริงให้ส่ง Success ปลอมไปก่อน
        return {"status": "mock_success", "message": "จำลองการเปิดลิ้นชักเงินสำเร็จ (ระบบทดสอบ)"}

@router.get("/hardware/scale/read")
def read_digital_scale(com_port: str = "COM3", baudrate: int = 9600):
    """
    (8.2) อ่านค่าน้ำหนักจากตาชั่งดิจิทัลผ่านพอร์ต RS232/USB
    แคชเชียร์วางเนื้อหมูบนตาชั่ง -> หน้าจอ POS เรียก API นี้ -> ได้น้ำหนักไปคำนวณราคาอัตโนมัติ
    """
    try:
        # เชื่อมต่อ Serial Port (ตาชั่งส่วนใหญ่มักใช้ Baudrate 9600)
        ser = serial.Serial(port=com_port, baudrate=baudrate, timeout=1)
        
        # อ่านค่าจากตาชั่ง (โดยทั่วไปตาชั่งจะส่งค่ามาเป็น String เช่น "   1.250 kg")
        raw_data = ser.readline().decode('utf-8', errors='ignore').strip()
        ser.close()
        
        if not raw_data:
            raise HTTPException(status_code=400, detail="ตาชั่งไม่ส่งข้อมูล กรุณาตรวจสอบสายเชื่อมต่อหรือวางสินค้าใหม่")
            
        # สกัดเฉพาะตัวเลข (เช่น "1.250")
        import re
        match = re.search(r"[-+]?\d*\.\d+|\d+", raw_data)
        weight = float(match.group()) if match else 0.0
        
        return {
            "status": "success",
            "weight_kg": weight,
            "raw_data": raw_data,
            "message": f"อ่านน้ำหนักสำเร็จ: {weight} กิโลกรัม"
        }
    except Exception as e:
        print(f"Scale Error: {e}")
        # Mock Data สำหรับตอนที่ยังไม่ได้เสียบตาชั่งจริง
        return {
            "status": "mock_success", 
            "weight_kg": 1.25, 
            "message": "จำลองการอ่านค่าน้ำหนัก 1.25 kg (ยังไม่ได้ต่อฮาร์ดแวร์จริง)"
        }
