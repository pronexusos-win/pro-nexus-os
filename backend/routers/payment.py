from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import uuid
from middleware.tenant import verify_tenant_header

router = APIRouter()

@router.post("/verify-slip")
def verify_transfer_slip(
    expected_amount: float,
    slip_image: UploadFile = File(...),
    tenant_id: str = Depends(verify_tenant_header)
):
    # ในสเกล Enterprise เราจะส่งรูปนี้ไปให้ SlipOK API หรือ Bank API ตรวจสอบ QR Code
    # ตอนนี้เราจำลอง (Mock) ว่า OCR อ่านสลิปสำเร็จและยอดเงินตรงกัน!
    mock_bank_ref = f"REF{uuid.uuid4().hex[:8].upper()}"
    
    return {
        "status": "success",
        "message": "ตรวจสอบสลิปสำเร็จ (จำลอง OCR)",
        "file_name": slip_image.filename,
        "verification_result": {
            "is_valid": True,
            "bank_ref": mock_bank_ref,
            "amount_on_slip": expected_amount,
            "sender_bank": "KBank",
            "receiver_bank": "SCB (Company Account)"
        }
    }
