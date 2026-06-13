from datetime import date
from pydantic import BaseModel, EmailStr

class SendOTPRequest(BaseModel):
    phone: str

class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str
    token : str

class PasswordLoginRequest(BaseModel):
    phone: str
    password: str

# class TokenResponse(BaseModel):
#     access_token: str
#     token_type: str = "bearer"

from pydantic import BaseModel
from typing import Optional

class NurseVisitCreate(BaseModel):
    patient_id: str
    duty_id: Optional[str] = None
    ward: Optional[str] = None
    room_no: Optional[str] = None
    visit_type: str
    notes: Optional[str] = None

    
class NurseConsentRequest(BaseModel):
    shift_type: str                 # DAY / NIGHT / 24_HOURS
    duty_hours: int

    salary_type: str               # DAILY / MONTHLY
    salary_amount: float
    payment_mode: str              # CASH / BANK / UPI
    salary_date: int               # 1–31

    confidentiality_accepted: bool
    no_direct_payment_accepted: bool
    police_termination_accepted: bool

    signature_image: Optional[str] = None
class NurseCreateWithConsentRequest(BaseModel):
    # USER
    phone: str
    email: Optional[EmailStr]

    # PROFILE
    nurse_type: str
    joining_date: Optional[date]

    # 🔥 CONSENT TERMS (ADMIN SETS)
    shift_type: str                # DAY / NIGHT / 24_HOURS
    duty_hours: int                # 8 / 12 / 24

    salary_type: str               # DAILY / MONTHLY
    salary_amount: float
    payment_mode: str              # CASH / BANK / UPI
    salary_date: int  
    
                 # 1–31
class SignatureUpdateSchema(BaseModel):
    signature_path: str

class EquipmentRequestCreate(BaseModel):
    equipment_id: str


class EquipmentRequestUpdate(BaseModel):
    status: Optional[bool] = None


class EquipmentResponse(BaseModel):
    id: str
    patient_id: str
    equipment_id: str
    equipment_title: str
    equipment_image: str
    status: bool

class EquipmentCreate(BaseModel):
    title: str
    price: float


class EquipmentUpdate(BaseModel):
    title: Optional[str] = None

    price : Optional[float] = None


class EquipmentResponse(BaseModel):
    id: str
    title: str

class HospitalCreate(BaseModel):
    name: str
    aname: Optional[str] = None
    acontact: Optional[str] = None
    address: str
    branch: str


class HospitalResponse(HospitalCreate):
    id: str