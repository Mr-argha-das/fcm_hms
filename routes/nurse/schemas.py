
from pydantic import BaseModel, Field
from typing import Optional, List
 


class CreateSalaryRequest(BaseModel):
    nurse_id      : str
    month         : str   = Field(..., example="2025-06", description="Format: YYYY-MM")
    basic_salary  : float = Field(default=0, ge=0, description="0 dene par duty se auto-calculate hogi")
    deductions    : float = Field(default=0, ge=0)
    advance_taken : float = Field(default=0, ge=0)
 
 
class PaySalaryRequest(BaseModel):
    amount_paid : float          = Field(..., gt=0, description="Partial ya full payment amount")
    payslip_pdf : Optional[str]  = Field(None, description="S3/Cloudinary PDF URL")
 
 
class UpdateSalaryRequest(BaseModel):
    basic_salary  : Optional[float] = None
    deductions    : Optional[float] = None
    advance_taken : Optional[float] = None
    payslip_pdf   : Optional[str]   = None
 
 
class UploadSlipRequest(BaseModel):
    payslip_pdf : str = Field(..., description="S3/Cloudinary PDF URL")
 
 
# ─────────────────────────────────────────────
#  RESPONSE SCHEMAS
# ─────────────────────────────────────────────
 
class DutyBreakdownItem(BaseModel):
    duty_id      : str
    duty_type    : Optional[str]
    shift        : Optional[str]
    price_perday : float
    days         : int
    salary       : float
 
 
class AttendanceInfo(BaseModel):
    total_days   : int
    present_days : int
    absent_days  : int
 
 
class SalarySummaryData(BaseModel):
    nurse_id           : str
    nurse_name         : str
    month              : str
    total_days         : int
    present_days       : int
    absent_days        : int
    calculated_salary  : float
    duty_breakdown     : List[DutyBreakdownItem]
    basic_salary       : float
    deductions         : float
    advance_taken      : float
    net_salary         : float
    total_paid         : float
    pending_amount     : float
    is_fully_paid      : bool
    payslip_pdf        : Optional[str]
    salary_record_id   : Optional[str]
 
 
class SalaryHistoryItem(BaseModel):
    salary_id      : str
    month          : str
    basic_salary   : Optional[float]
    deductions     : Optional[float]
    advance_taken  : Optional[float]
    net_salary     : Optional[float]
    total_paid     : float
    pending_amount : float
    is_fully_paid  : bool
    payslip_pdf    : Optional[str]
    created_at     : Optional[str]
 
 
class OverallSummary(BaseModel):
    total_earned  : float
    total_paid    : float
    total_pending : float
 
 
class SalaryHistoryData(BaseModel):
    nurse_id   : str
    nurse_name : str
    summary    : OverallSummary
    history    : List[SalaryHistoryItem]
 
 
class PendingItem(BaseModel):
    salary_id      : str
    nurse_id       : str
    nurse_name     : str
    month          : str
    net_salary     : Optional[float]
    total_paid     : float
    pending_amount : float
    payslip_pdf    : Optional[str]
 

 
class LeadCreateRequest(BaseModel):
    name: str
    phone: str
    gender: Optional[str] = None
    age: Optional[int] = None
    city: str
    address: str
    service: str
    source: str
    notes: Optional[str] = None