import re

# บัญชีคำต้องห้ามและความเสี่ยงทางกฎหมาย
RESTRICTED_DICTIONARY = [
    {
        "pattern": r"(ปันผล|เงินปันผล|dividend)",
        "risk_level": "CRITICAL",
        "law_ref": "ป.พ.พ. มาตรา 1102 & กฎหมายบริษัทจำกัด",
        "reason": "คำว่า 'เงินปันผล' ใช้ได้เฉพาะการจัดสรรกำไรสะสมประจำปีแก่ผู้ถือหุ้นตาม บอจ.5 เท่านั้น ห้ามนำมาใช้กับกระเป๋าตัวแทนหรือสาขา",
        "suggested": "ค่าตอบแทนผลงาน (Performance Incentive) หรือ คอมมิชชันการตลาด (Marketing Commission)"
    },
    {
        "pattern": r"(ถือหุ้น|ซื้อหุ้น|ลงขัน|ร่วมทุน|จองหุ้น|shareholder|equity)",
        "risk_level": "CRITICAL",
        "law_ref": "พ.ร.บ. หลักทรัพย์และตลาดหลักทรัพย์ (ก.ล.ต.)",
        "reason": "บริษัทจำกัดห้ามชี้ชวนประชาชนทั่วไปซื้อหุ้นหรือร่วมระดมทุน เสี่ยงโทษอาญา",
        "suggested": "สิทธิผู้ร่วมเปิดสาขา (Franchise/Hub Partner) หรือ ค่าบริหารจัดการสาขา"
    },
    {
        "pattern": r"(การันตีผลตอบแทน|การันตีกำไร|ผลตอบแทนคงที่|passive income)",
        "risk_level": "CRITICAL",
        "law_ref": "พ.ร.ก. การกู้ยืมเงินที่เป็นการฉ้อโกงประชาชน (แชร์ลูกโซ่)",
        "reason": "ห้ามโฆษณาการันตีผลตอบแทนโดยไม่มีการอิงยอดขายสินค้าจริง",
        "suggested": "โบนัสตามเป้าหมายยอดขายจริง (Milestone Sales Rebate)"
    },
    {
        "pattern": r"(เหรียญลงทุน|โทเคน|crypto|token)",
        "risk_level": "WARNING",
        "law_ref": "พ.ร.ก. การประกอบธุรกิจสินทรัพย์ดิจิทัล",
        "reason": "อาจเข้าข่ายการออกโทเคนดิจิทัลเพื่อการลงทุนโดยไม่ได้รับอนุญาต",
        "suggested": "แต้มสะสมสมาชิก (Loyalty Points) หรือ เครดิตส่วนลด (Store Credit)"
    },
    {
        "pattern": r"(ค่าหัว|ค่าชวนคน|ค่าแนะนำสมาชิก)",
        "risk_level": "WARNING",
        "law_ref": "พ.ร.บ. ขายตรงและตลาดแบบตรง",
        "reason": "รายได้ต้องเกิดจากการหมุนเวียนของสินค้าจริง ไม่ใช่การคิดหัวคิวจากการชักชวนคน",
        "suggested": "ค่าบริการส่งเสริมการขายสินค้า (Product Marketing Fee)"
    }
]

def scan_text_compliance(text: str) -> dict:
    """
    ตรวจจับคำเสี่ยงทางกฎหมาย และให้คำแนะนำแปลงคำปลอดภัยทันที
    """
    clean_text = text.strip()
    detected_issues = []

    for rule in RESTRICTED_DICTIONARY:
        match = re.search(rule["pattern"], clean_text, re.IGNORECASE)
        if match:
            detected_issues.append({
                "detected_keyword": match.group(0),
                "risk_level": rule["risk_level"],
                "law_reference": rule["law_ref"],
                "reason": rule["reason"],
                "suggested_alternative": rule["suggested"]
            })

    is_compliant = len(detected_issues) == 0

    return {
        "input_text": clean_text,
        "is_compliant": is_compliant,
        "violations_count": len(detected_issues),
        "issues": detected_issues,
        "action": "ALLOW" if is_compliant else "BLOCK_AND_SUGGEST"
    }
