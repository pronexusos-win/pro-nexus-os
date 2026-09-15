from datetime import datetime, date
from backend.app.core.database import get_db_connection

def generate_monthly_tax_summary(year: int, month: int, company_slug: str = "tp_extra"):
    """
    ดึงยอดคำนวณภาษีจริงจากฐานข้อมูล:
    - ภ.พ. 30: ภาษีขายจากค่าธรรมเนียมแพลตฟอร์ม (Bucket 5 Platform GP)
    - ภ.ง.ด. 53: ภาษีหัก ณ ที่จ่าย 3% จากคู่ค้า/ซัพพลายเออร์
    - ภ.ง.ด. 1: ภาษีหัก ณ ที่จ่ายเงินเดือนพนักงาน
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. ยอด ภ.พ. 30 (VAT 7% บน Platform GP)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(platform_net_gp), 0) as base_gp,
                    COALESCE(SUM(platform_vat_amount), 0) as vat_amount
                FROM order_financial_splits
                WHERE company_slug = %s AND YEAR(created_at) = %s AND MONTH(created_at) = %s;
            """, (company_slug, year, month))
            vat_data = cursor.fetchone()

            # 2. ยอด ภ.ง.ด. 53 (WHT 3%)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(platform_net_gp), 0) as base_service,
                    COALESCE(SUM(withholding_tax_amount), 0) as wht_amount
                FROM order_financial_splits
                WHERE company_slug = %s AND YEAR(created_at) = %s AND MONTH(created_at) = %s;
            """, (company_slug, year, month))
            wht_data = cursor.fetchone()

            # 3. ยอด ภ.ง.ด. 1 (เงินเดือนพนักงาน)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(base_salary), 0) as total_salaries,
                    COALESCE(SUM(withholding_tax), 0) as salary_wht
                FROM employee_master
                WHERE company_slug = %s AND employment_status IN ('PROBATION', 'CONFIRMED');
            """, (company_slug,))
            emp_data = cursor.fetchone()

    return {
        "period": f"{month:02d}/{year}",
        "pp30_vat": {
            "base_sales": float(vat_data["base_gp"]),
            "vat_7pct": float(vat_data["vat_amount"]),
            "efiling_deadline": f"{year}-{month+1:02d}-23" if month < 12 else f"{year+1}-01-23"
        },
        "pnd53_wht": {
            "base_service": float(wht_data["base_service"]),
            "tax_3pct": float(wht_data["wht_amount"]),
            "efiling_deadline": f"{year}-{month+1:02d}-15" if month < 12 else f"{year+1}-01-15"
        },
        "pnd1_salary": {
            "total_salaries": float(emp_data["total_salaries"]),
            "tax_withheld": float(emp_data["salary_wht"]),
            "efiling_deadline": f"{year}-{month+1:02d}-15" if month < 12 else f"{year+1}-01-15"
        }
    }

def export_etax_xml_template(doc_number: str, seller_tax_id: str, buyer_tax_id: str, amount: float, vat: float):
    """
    สร้างโครงร่าง XML มาตรฐาน e-Tax Invoice by Email / Web Upload ของกรมสรรพากร (ETDA Standard)
    """
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rsm:TaxInvoice_CrossIndustryInvoice xmlns:rsm="urn:etda:uncefact:data:standard:TaxInvoice_CrossIndustryInvoice:2">
    <rsm:ExchangedDocument>
        <rsm:ID>{doc_number}</rsm:ID>
        <rsm:IssueDateTime>{datetime.now().isoformat()}</rsm:IssueDateTime>
    </rsm:ExchangedDocument>
    <rsm:SupplyChainTradeTransaction>
        <rsm:ApplicableHeaderTradeAgreement>
            <rsm:SellerTradeParty><rsm:SpecifiedTaxRegistration><rsm:ID>{seller_tax_id}</rsm:ID></rsm:SpecifiedTaxRegistration></rsm:SellerTradeParty>
            <rsm:BuyerTradeParty><rsm:SpecifiedTaxRegistration><rsm:ID>{buyer_tax_id}</rsm:ID></rsm:SpecifiedTaxRegistration></rsm:BuyerTradeParty>
        </rsm:ApplicableHeaderTradeAgreement>
        <rsm:ApplicableHeaderTradeSettlement>
            <rsm:SpecifiedTradeSettlementHeaderMonetarySummation>
                <rsm:LineTotalAmount>{amount:.2f}</rsm:LineTotalAmount>
                <rsm:TaxTotalAmount>{vat:.2f}</rsm:TaxTotalAmount>
                <rsm:GrandTotalAmount>{(amount + vat):.2f}</rsm:GrandTotalAmount>
            </rsm:SpecifiedTradeSettlementHeaderMonetarySummation>
        </rsm:ApplicableHeaderTradeSettlement>
    </rsm:SupplyChainTradeTransaction>
</rsm:TaxInvoice_CrossIndustryInvoice>"""
    return xml_content
