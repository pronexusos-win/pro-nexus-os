import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from middleware.rbac import verify_role
from middleware.tenant import verify_tenant_header
from core.database import get_db_connection

router = APIRouter()

@router.get("/export/tax-50-bis", dependencies=[Depends(verify_role(["super_admin", "company_admin"]))])
def export_tax_report_csv(tenant_id: str = Depends(verify_tenant_header)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ดึงประวัติการจ่ายเงินทั้งหมดของ Tenant นี้
            sql = """
                SELECT c.created_at, c.transaction_id, m.member_id, m.name, 
                       c.gross_amount, c.tax_amount, c.net_amount, c.type
                FROM commissions c
                JOIN members m ON c.member_id = m.member_id
                WHERE m.tenant_id = %s
                ORDER BY c.created_at DESC
            """
            cursor.execute(sql, (tenant_id,))
            records = cursor.fetchall()

        # สร้างไฟล์ CSV ในหน่วยความจำ
        stream = io.StringIO()
        writer = csv.writer(stream)
        
        # หัวตาราง (Header)
        writer.writerow([
            "วันที่ทำรายการ", 
            "รหัสอ้างอิง (Transaction ID)", 
            "รหัสสมาชิก", 
            "ชื่อ-นามสกุล", 
            "เลขประจำตัวผู้เสียภาษี", 
            "ประเภทรายได้",
            "ยอดเงินได้ก่อนหักภาษี (Gross)", 
            "ภาษีหัก ณ ที่จ่าย 3% (Tax)", 
            "ยอดเงินสุทธิ (Net)"
        ])
        
        for row in records:
            writer.writerow([
                row.get("created_at", "N/A"),
                row["transaction_id"],
                row["member_id"],
                row["name"],
                "รอการทำ KYC", # ฟิลด์นี้เตรียมไว้เชื่อมกับระบบ KYC บัตรประชาชน
                row["type"],
                f"{row['gross_amount']:.2f}",
                f"{row['tax_amount']:.2f}",
                f"{row['net_amount']:.2f}"
            ])
        
        stream.seek(0)
        
        # ส่งไฟล์กลับไปให้เบราว์เซอร์ดาวน์โหลด
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename=Tax_50Bis_{tenant_id}.csv"
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
