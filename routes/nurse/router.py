from fastapi import APIRouter, Depends, HTTPException,status
from datetime import datetime, timedelta
from core.dependencies import get_current_user
from models import (
    NurseProfile, NurseDuty, NurseAttendance,
    NurseSalary, NurseConsent, NurseVisit, PatientProfile, User
)
from routes.auth.schemas import NurseVisitCreate
from .utils import ensure_consent_active, ensure_duty_time
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import date
class NurseCreateRequest(BaseModel):
    phone: str
    email: Optional[EmailStr] = None

    nurse_type: str = Field(..., example="GNM")
    aadhaar_number: Optional[str] = None

    qualification_docs: List[str] = []
    experience_docs: List[str] = []

    joining_date: Optional[date] = None

class NurseResponse(BaseModel):
    nurse_id: str
    user_id: str
    verification_status: str
router = APIRouter(prefix="/nurse", tags=["Nurse"])
@router.post("/create", response_model=NurseResponse)
def create_nurse(payload: NurseCreateRequest):

    # 1️⃣ Check duplicate phone
    if User.objects(phone=payload.phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )

    # 2️⃣ Create User
    user = User(
        role="NURSE",
        phone=payload.phone,
        email=payload.email,
        otp_verified=False,
        is_active=True,
        created_at=datetime.utcnow()
    )
    user.save()

    # 3️⃣ Create Nurse Profile
    nurse = NurseProfile(
        user=user,
        nurse_type=payload.nurse_type,
        aadhaar_number=payload.aadhaar_number,
        qualification_docs=payload.qualification_docs,
        experience_docs=payload.experience_docs,
        joining_date=payload.joining_date,
        verification_status="PENDING",
        police_verification_status="PENDING",
        created_at=datetime.utcnow()
    )
    nurse.save()

    return NurseResponse(
        nurse_id=str(nurse.id),
        user_id=str(user.id),
        verification_status=nurse.verification_status
    )

@router.post("/profile/create")
def create_profile(nurse_type: str, user=Depends(get_current_user)):
    if user.role != "NURSE":
        raise HTTPException(403, "Only nurses allowed")

    if NurseProfile.objects(user=user).first():
        raise HTTPException(400, "Profile already exists")

    profile = NurseProfile(
        user=user,
        nurse_type=nurse_type,
        joining_date=datetime.utcnow().date()
    ).save()

    return {"message": "Profile created", "id": str(profile.id)}
@router.get("/profile/me")
def my_profile(user=Depends(get_current_user)):
    return NurseProfile.objects(user=user).first()
@router.get("/duty/current")
def current_duty(user=Depends(get_current_user)):
    nurse = NurseProfile.objects(user=user).first()
    return NurseDuty.objects(nurse=nurse, is_active=True).first()
@router.post("/duty/check-in")
def duty_check_in(user=Depends(get_current_user)):
    nurse = NurseProfile.objects(user=user).first()

    if nurse.police_verification_status == "FAILED":
        raise HTTPException(403, "Police verification failed")

    ensure_consent_active(nurse)

    duty = NurseDuty.objects(nurse=nurse, is_active=True).first()
    if not duty:
        raise HTTPException(400, "No active duty")

    ensure_duty_time(duty)

    if duty.check_in:
        raise HTTPException(400, "Already checked in")

    duty.check_in = datetime.utcnow()
    duty.save()

    NurseAttendance(
        nurse=nurse,
        date=datetime.utcnow().date(),
        check_in=duty.check_in,
        method="FACE"
    ).save()

    return {"message": "Checked in successfully"}
@router.post("/duty/check-out")
def duty_check_out(user=Depends(get_current_user)):
    nurse = NurseProfile.objects(user=user).first()
    duty = NurseDuty.objects(nurse=nurse, is_active=True).first()

    if not duty or not duty.check_in:
        raise HTTPException(400, "Invalid check-out")

    duty.check_out = datetime.utcnow()
    duty.is_active = False
    duty.save()

    attendance = NurseAttendance.objects(
        nurse=nurse,
        date=datetime.utcnow().date()
    ).first()

    if attendance:
        attendance.check_out = duty.check_out
        attendance.save()

    return {"message": "Checked out & duty closed"}
@router.get("/salary/my")
def my_salary(user=Depends(get_current_user)):
    nurse = NurseProfile.objects(user=user).first()
    return NurseSalary.objects(nurse=nurse)
@router.post("/salary/advance-request")
def advance_request(amount: float, user=Depends(get_current_user)):
    nurse = NurseProfile.objects(user=user).first()

    salary = NurseSalary.objects(nurse=nurse).order_by("-created_at").first()
    if not salary:
        raise HTTPException(400, "Salary record not found")

    salary.advance_taken += amount
    salary.net_salary -= amount
    salary.save()

    return {"message": "Advance granted"}
@router.post("/consent/sign")
def sign_consent(
    shift_type: str,
    duty_hours: int,
    salary_amount: float,
    user=Depends(get_current_user)
):
    nurse = NurseProfile.objects(user=user).first()

    consent = NurseConsent(
        nurse=nurse,
        shift_type=shift_type,
        duty_hours=duty_hours,
        salary_type="MONTHLY",
        salary_amount=salary_amount,
        confidentiality_accepted=True,
        no_direct_payment_accepted=True,
        police_termination_accepted=True,
        status="SIGNED"
    ).save()

    return {"message": "Consent signed", "id": str(consent.id)}


@router.post("/nurse/visit")
def nurse_create_visit(
    payload: NurseVisitCreate,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "NURSE":
        raise HTTPException(status_code=403, detail="Only nurses allowed")

    nurse = NurseProfile.objects(user=current_user).first()
    patient = PatientProfile.objects(id=payload.patient_id).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    visit = NurseVisit(
        nurse=nurse,
        patient=patient,
        duty=payload.duty_id,
        ward=payload.ward,
        room_no=payload.room_no,
        visit_type=payload.visit_type,
        notes=payload.notes,
        created_by=current_user
    )
    visit.save()

    return {
        "message": "Visit recorded successfully",
        "visit_id": str(visit.id)
    }
@router.get("/dashboard")
def nurse_dashboard(current_user: User = Depends(get_current_user)):

    # 1️⃣ Role check
    if current_user.role != "NURSE":
        raise HTTPException(status_code=403, detail="Access denied")

    # 2️⃣ Nurse profile
    nurse = NurseProfile.objects(user=current_user).first()
    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    today = date.today()
    now = datetime.utcnow()

    # 3️⃣ Attendance (today)
    attendance = NurseAttendance.objects(
        nurse=nurse,
        date=today
    ).first()

    worked_minutes = 0
    if attendance and attendance.check_in:
        end_time = attendance.check_out or now
        worked_minutes = int((end_time - attendance.check_in).total_seconds() / 60)

    # 4️⃣ TODAY VISITS (🔥 REAL SOURCE = NurseVisit)
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    visits = NurseVisit.objects(
        nurse=nurse,
        visit_time__gte=today_start,
        visit_time__lte=today_end
    ).order_by("-visit_time")

    today_visits = []
    for v in visits:
        patient_user = v.patient.user if v.patient else None

        today_visits.append({
            "visit_id": str(v.id),
            "patient_id": str(v.patient.id),
            "patient_name": patient_user.email if patient_user else None,
            "ward": v.ward,
            "room_no": v.room_no,
            "visit_type": v.visit_type,
            "visit_time": v.visit_time
        })

    # 5️⃣ WEEKLY WORK HOURS (Attendance based)
    start_of_week = today - timedelta(days=today.weekday())
    weekly_hours = []

    for i in range(7):
        d = start_of_week + timedelta(days=i)
        att = NurseAttendance.objects(nurse=nurse, date=d).first()

        hours = 0
        if att and att.check_in and att.check_out:
            hours = round(
                (att.check_out - att.check_in).total_seconds() / 3600, 2
            )

        weekly_hours.append({
            "day": d.strftime("%a"),
            "hours": hours
        })

    # 6️⃣ Final Response
    return {
        "nurse": {
            "nurse_id": str(nurse.id),
            "name": current_user.email.split("@")[0].title(),
            "nurse_type": nurse.nurse_type,
            "status": "ACTIVE" if attendance and attendance.check_in and not attendance.check_out else "INACTIVE",
            "worked_time": f"{worked_minutes // 60}h {worked_minutes % 60}m"
        },

        "today_visits": today_visits,

        "attendance": {
            "check_in": attendance.check_in if attendance else None,
            "check_out": attendance.check_out if attendance else None,
            "is_checked_in": bool(attendance and attendance.check_in and not attendance.check_out)
        },

        "weekly_hours": weekly_hours
    }
