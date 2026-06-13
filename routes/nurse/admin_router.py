import os
from typing import List
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from datetime import date, datetime

from pymongo.auth import Optional
from core.dependencies import admin_required, get_current_user
from models import HospitalModel, NurseProfile, NurseDuty, NurseSalary, NurseConsent, NurseVisit, PatientProfile
from routes.auth.schemas import NurseVisitCreate, SignatureUpdateSchema
from bson import ObjectId
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
router = APIRouter(prefix="/admin/nurse", tags=["Admin-Nurse"])


@router.post("/approve")
def approve_nurse(nurse_id: str, admin=Depends(admin_required)):
    nurse = NurseProfile.objects(id=nurse_id).first()
    nurse.verification_status = "APPROVED"
    nurse.save()
    return {"message": "Nurse approved"}

@router.post("/reject")
def reject_nurse(nurse_id: str, admin=Depends(admin_required)):
    nurse = NurseProfile.objects(id=nurse_id).first()
    nurse.verification_status = "REJECTED"
    nurse.save()
    return {"message": "Nurse rejected"}
@router.post("/police-status")
def police_status(nurse_id: str, status: str, admin=Depends(admin_required)):
    nurse = NurseProfile.objects(id=nurse_id).first()
    nurse.police_verification_status = status
    nurse.save()

    if status == "FAILED":
        nurse.user.is_active = False
        nurse.user.save()

    return {"message": "Police status updated"}
@router.post("/duty/assign")
def assign_duty(
    nurse_id: str,
    patient_id: str,
    duty_type: str,
    start: datetime,
    end: datetime,
    admin=Depends(admin_required)
):
    nurse = NurseProfile.objects(id=nurse_id).first()

    if NurseDuty.objects(nurse=nurse, is_active=True):
        raise HTTPException(400, "Nurse already on active duty")

    duty = NurseDuty(
        nurse=nurse,
        patient=patient_id,
        duty_type=duty_type,
        duty_start=start,
        duty_end=end
    ).save()

    return {"message": "Duty assigned", "id": str(duty.id)}
@router.post("/duty/change")
def change_duty(
    duty_id: str,
    start: datetime,
    end: datetime,
    admin=Depends(admin_required)
):
    duty = NurseDuty.objects(id=duty_id).first()
    duty.duty_start = start
    duty.duty_end = end
    duty.save()
    return {"message": "Duty updated"}
@router.post("/salary/generate")
def generate_salary(
    nurse_id: str,
    month: str,
    amount: float,
    admin=Depends(admin_required)
):
    nurse = NurseProfile.objects(id=nurse_id).first()

    salary = NurseSalary(
        nurse=nurse,
        month=month,
        basic_salary=amount,
        deductions=0,
        net_salary=amount
    ).save()

    return {"message": "Salary generated"}
@router.post("/salary/mark-paid")
def mark_paid(salary_id: str, admin=Depends(admin_required)):
    salary = NurseSalary.objects(id=salary_id).first()
    salary.is_paid = True
    salary.save()
    return {"message": "Salary marked paid"}
@router.post("/consent/revoke")
def revoke_consent(nurse_id: str, admin=Depends(admin_required)):
    consent = NurseConsent.objects(nurse=nurse_id, status="SIGNED").first()
    if consent:
        consent.status = "REVOKED"
        consent.save()

    NurseDuty.objects(nurse=nurse_id, is_active=True).update(is_active=False)
    return {"message": "Consent revoked & duty blocked"}

@router.post("/admin/visit")
def admin_create_visit(
    payload: NurseVisitCreate,
    nurse_id: str,
    visit_time: datetime,
    admin= Depends(admin_required)
):
   # Admin can create visits for any nurse
    if not nurse:
       raise HTTPException(status_code=404, detail="Nurse not found")
    if not patient:
       raise HTTPException(status_code=404, detail="Patient not found")
   

    nurse = NurseProfile.objects(id=nurse_id).first()
    patient = PatientProfile.objects(id=payload.patient_id).first()

    visit = NurseVisit(
        nurse=nurse,
        patient=patient,
        duty=payload.duty_id,
        ward=payload.ward,
        room_no=payload.room_no,
        visit_type=payload.visit_type,
        notes=payload.notes,
        visit_time=visit_time,
        created_by=admin
    )
    visit.save()

    return {"message": "Visit created by admin"}
from dotenv import load_dotenv
load_dotenv()


# EMAIL_USER = "abhaykoli214@gmail.com"
# EMAIL_PASS = "qlan xrpx mzga jpls"
EMAIL_USER = "wcare823@gmail.com"
EMAIL_PASS = "olco iphu vjwj jlov"

def send_email(to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
    """
    Generic reusable email sender
    """

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject

    content_type = "html" if is_html else "plain"
    msg.attach(MIMEText(body, content_type))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()

        print("✅ Email sent")
        return True

    except Exception as e:
        print("❌ Email Error:", e)
        return False


# ==================================
# Beautiful Account Approved Template
# ==================================
def send_account_approved_email(to_email: str, username: str = "User") -> bool:
    """
    Sends a beautiful account approved email
    """

    subject = "🎉 Your Account Has Been Approved"

    body = f"""
    <div style="font-family: Arial, sans-serif; background:#f4f6f8; padding:40px;">
      <div style="max-width:520px; margin:auto; background:white; padding:35px;
                  border-radius:12px; box-shadow:0 8px 20px rgba(0,0,0,0.08);
                  text-align:center;">

        <h2 style="color:#22c55e;">✅ Account Approved</h2>

        <p style="font-size:16px; color:#333;">
            Hi <b>{username}</b>,
        </p>

        <p style="font-size:15px; color:#555;">
            Your account has been <b>successfully approved</b> 🎉<br>
            You can now login and start using our services.
        </p>


        <p style="margin-top:30px; font-size:12px; color:#888;">
            Thanks for choosing us ❤️
        </p>
      </div>
    </div>
    """

    return send_email(to_email, subject, body, is_html=True)



@router.post("/{nurse_id}/update")
def update_nurse_admin(
    nurse_id: str,
    aadhaar_verified: str = Form("false"),
    police_verification_status: str | None = Form(None),
    nurse_type: str | None = Form(None),
    salary_type: str | None = Form(None),
    payment_mode: str | None = Form(None),  
    joining_date: str | None = Form(None),
    resignation_date: str | None = Form(None),
    is_active: str = Form("false"),
    # salary_type: str = Form(...),
    # salary_amount: float = Form(...),
    # salary_date: int = Form(...),
    experience_letter: str | None = Form(None),
    paySlip : Optional[List[str]] = Form(None),
    salary_amount: float | None = Form(None),
    salary_date: int | None = Form(None),
    # payment_mode: str = Form(...),
    digital_signature_verify: bool = Form(False),
    police: Optional[List[str]] = Form(None),  # ✅ FIXED
    hospital: str | None = Form(None),
    account_holder_name: str | None = Form(None),
    bank_name: str | None = Form(None),
    branch_name: str | None = Form(None),
    account_number: str | None = Form(None),
    ifsc_code: str | None = Form(None),
    upi_id: str | None = Form(None),
):
    nurse = NurseProfile.objects(id=nurse_id).first()
    if not nurse:
        raise HTTPException(404, "Nurse not found")

    nurse.aadhaar_verified = aadhaar_verified == "true"
    nurse.police_verification_status = police_verification_status
    nurse.nurse_type = nurse_type

    nurse.joining_date = date.fromisoformat(joining_date) if joining_date else None
    nurse.resignation_date = date.fromisoformat(resignation_date) if resignation_date else None
    nurse.digital_signature_verify = digital_signature_verify
    nurse.account_holder_name = account_holder_name or ""
    nurse.bank_name = bank_name or ""
    nurse.branch_name = branch_name or ""
    nurse.account_number = account_number or ""
    nurse.ifsc_code = ifsc_code or ""
    nurse.upi_id = upi_id or ""
    # Experience letter (single file)
    if experience_letter:
        nurse.experience_letter = experience_letter

# PaySlip (multiple files)
    if paySlip:
        if isinstance(paySlip, list):
            nurse.paySlip = list(set(paySlip))
        elif isinstance(paySlip, str):
            nurse.paySlip = [paySlip]

    # ✅ POLICE SAFE CHECK
    if police:
        if isinstance(police, list):
            nurse.police = list(set(police))
        elif isinstance(police, str):
            nurse.police = [police]
    else:
        nurse.police = []

    nurse.save()

    # 🔥 USER UPDATE
    if nurse.user:
        nurse.user.is_active = is_active == "true"

        if hospital:
            nurse.user.hospital = HospitalModel.objects(id=hospital).first()
        else:
            nurse.user.hospital = None

        nurse.user.save()

    # ✅ CONSENT UPDATE
    consent = NurseConsent.objects(nurse=nurse).order_by("-created_at").first()
    if not consent:
        consent = NurseConsent(
            nurse=nurse,
            shift_type="DAY",
            duty_hours=8,
            status="PENDING"
        )

    consent.salary_type = salary_type
    consent.salary_amount = salary_amount
    consent.payment_mode = payment_mode
    consent.salary_date = salary_date
    consent.save()

    return {
        "success": True,
        "police_received": nurse.police  # debug ke liye
    }


@router.put("/signature/{nurse_id}")
async def update_nurse_signature(nurse_id: str, body: SignatureUpdateSchema):
    try:
        nurse = NurseProfile.objects(id=ObjectId(nurse_id)).first()

        if not nurse:
            raise HTTPException(status_code=404, detail="Nurse not found")

        nurse.digital_signature = body.signature_path
        nurse.save()

        return {
            "success": True,
            "message": "Signature uploaded successfully",
            "digital_signature": nurse.digital_signature
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
