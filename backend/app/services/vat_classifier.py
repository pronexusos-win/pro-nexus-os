import re

# กฎการจำแนกภาษีมูลค่าเพิ่มตามประมวลรัษฎากร
TAX_CLASSIFICATION_RULES = [
    {
        "pattern": r"(ปุ๋ย|ดินปลูก|สารปรับปรุงดิน|อาหารสัตว์|ยาฆ่าหญ้า|ปุ๋ยหมัก|ปุ๋ยคอก)",
        "category": "VAT_EXEMPT_SEC81",
        "reason": "ม.81(1)(จ) ปุ๋ย ยา หรือเคมีภัณฑ์ที่ใช้สำหรับพืชหรือสัตว์",
        "license_needed": "FERTILIZER"
    },
    {
        "pattern": r"(ข้าวสาร|ข้าวกล้อง|ผักสด|ผลไม้สด|ไข่ไก่|ไข่เป็ด|เนื้อสด|พืชสด|เห็ดสด)",
        "category": "VAT_EXEMPT_SEC81",
        "reason": "ม.81(1)(ก) พืชผลทางการเกษตร สัตว์มีชีวิต หรือเนื้อสัตว์สด",
        "license_needed": None
    },
    {
        "pattern": r"(เหล้า|เบียร์|ไวน์|สุรา|วอดก้า)",
        "category": "VAT_STANDARD_7",
        "reason": "สินค้าอุปโภคบริโภคทั่วไป (มีภาษีสรรพสามิตและ VAT)",
        "license_needed": "ALCOHOL"
    },
    {
        "pattern": r"(บุหรี่|ยาสูบ|ซิการ์)",
        "category": "VAT_STANDARD_7",
        "reason": "ยาสูบเสียภาษีสรรพสามิตและมี VAT 7%",
        "license_needed": "TOBACCO"
    },
    {
        "pattern": r"(สบู่|ครีม|เซรั่ม|โลชั่น|แชมพู|ยาสีฟัน|น้ำหอม|เครื่องสำอาง)",
        "category": "VAT_STANDARD_7",
        "reason": "เครื่องสำอางและเวชสำอางต้องเสียภาษีมูลค่าเพิ่ม 7%",
        "license_needed": None
    },
    {
        "pattern": r"(กาแฟ|ชาเขียว|อาหารเสริม|วิตามิน|คอลลาเจน|โปรตีน)",
        "category": "VAT_STANDARD_7",
        "reason": "อาหารแปรรูปและผลิตภัณฑ์เสริมอาหารต้องเสียภาษีมูลค่าเพิ่ม 7%",
        "license_needed": None
    }
]

def classify_product_tax(product_name: str) -> dict:
    """
    วิเคราะห์ชื่อสินค้าและแนะนำการจัดเก็บภาษี (VAT) อัตโนมัติ
    """
    name = product_name.strip()
    
    for rule in TAX_CLASSIFICATION_RULES:
        if re.search(rule["pattern"], name, re.IGNORECASE):
            return {
                "product_name": name,
                "suggested_vat_category": rule["category"],
                "is_vat_exempt": rule["category"] == "VAT_EXEMPT_SEC81",
                "tax_exemption_reason": rule["reason"],
                "required_license": rule["license_needed"],
                "confidence": "HIGH"
            }
            
    # ค่าเริ่มต้น: สินค้าทั่วไปเสีย VAT 7% เสมอเพื่อความปลอดภัย
    return {
        "product_name": name,
        "suggested_vat_category": "VAT_STANDARD_7",
        "is_vat_exempt": False,
        "tax_exemption_reason": "สินค้าและบริการทั่วไปตามมาตรา 77/1 (เสียภาษี 7%)",
        "required_license": None,
        "confidence": "DEFAULT"
    }
