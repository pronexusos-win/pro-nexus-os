from pydantic import BaseModel
from typing import Optional

class MemberCreate(BaseModel):
    name: str
    tenant_id: str
    sponsor_id: Optional[str] = None
    line_user_id: str
    pin: str
