from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

# 1. User & Multi-tenant Company Model
class UserModel(BaseModel):
    id: Optional[int] = None
    line_user_id: str
    company_slug: str  # pro_nexus, tp_extra, luck_kio, peak_icon
    display_name: str
    role: str = "member"  # superadmin, admin, staff, member
    created_at: datetime = Field(default_factory=datetime.utcnow)

# 2. Slip & OCR Verification Model
class SlipVerificationModel(BaseModel):
    id: Optional[int] = None
    company_slug: str
    line_user_id: str
    image_url: str
    trans_amount: Optional[float] = None
    trans_date: Optional[str] = None
    trans_time: Optional[str] = None
    sender_bank: Optional[str] = None
    receiver_bank: Optional[str] = None
    receiver_account: Optional[str] = None
    verification_status: str = "pending"  # pending, verified, rejected
    raw_ocr_data: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# 3. Order Model (สำหรับ แบ่งปันชอป)
class OrderModel(BaseModel):
    id: Optional[int] = None
    order_no: str
    company_slug: str = "tp_extra"
    line_user_id: str
    total_amount: float
    status: str = "pending_payment"  # pending_payment, paid, shipping, completed, cancelled
    slip_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
