import re

def process_slip_image(image_bytes: bytes) -> dict:
    # จำลองการประมวลผล OCR สกัดข้อมูลสลิปธนาคาร
    # ในระบบจริงสามารถเชื่อมต่อกับ OCR Engine เช่น Tesseract หรือ Cloud Vision API
    mock_extracted_text = "โอนเงินสำเร็จ 1,000.00 บาท วันที่ 12/09/2026 ธนาคารกสิกรไทย"
    
    amount_match = re.search(r'([\d,]+\.\d{2})\s*บาท', mock_extracted_text)
    amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.00
    
    return {
        "status": "success",
        "raw_text": mock_extracted_text,
        "detected_amount": amount,
        "bank": "Kasikornbank"
    }
