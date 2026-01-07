from pydantic import BaseModel

class SendOTPRequest(BaseModel):
    phone: str

class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str

class PasswordLoginRequest(BaseModel):
    phone: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

from pydantic import BaseModel
from typing import Optional

class NurseVisitCreate(BaseModel):
    patient_id: str
    duty_id: Optional[str] = None
    ward: Optional[str] = None
    room_no: Optional[str] = None
    visit_type: str
    notes: Optional[str] = None