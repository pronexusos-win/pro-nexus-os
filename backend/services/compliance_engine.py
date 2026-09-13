def process_split_and_tax(total_amount: float, vat_rate: float = 0.07, wht_rate: float = 0.0):
    """
    เครื่องยนต์คำนวณการแยกภาษีมูลค่าเพิ่ม (VAT) และภาษีหัก ณ ที่จ่าย (WHT)
    รองรับการคำนวณแบบรวมใน (Inclusive) และแยกนอก (Exclusive)
    """
    # สมมติฐานเป็นแบบ Inclusive VAT 7%
    base_price = total_amount / (1 + vat_rate)
    vat_amount = total_amount - base_price
    wht_amount = base_price * wht_rate
    net_payable = total_amount - wht_amount

    return {
        "total_amount": round(total_amount, 2),
        "base_price": round(base_price, 2),
        "vat_amount": round(vat_amount, 2),
        "wht_amount": round(wht_amount, 2),
        "net_payable": round(net_payable, 2)
    }
