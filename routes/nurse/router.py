from calendar import calendar
from fastapi import APIRouter, Depends, HTTPException,status
from datetime import datetime, timedelta
from core.dependencies import get_current_user
from models import (
    NurseProfile, NurseDuty, NurseAttendance,
    NurseSalary, NurseConsent, NurseVisit, PatientProfile, User, PatientVitals, PatientDailyNote, PatientMedication
)

from routes.auth.schemas import NurseConsentRequest, NurseVisitCreate
from .utils import ensure_consent_active, ensure_duty_time
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import date
import calendar as cal
class NurseCreateRequest(BaseModel):

    phone: str = Field(..., example="9876543210")
    name: str = Field(..., example="Sruti Das")
    father_name: Optional[str] = Field(None, example="Ram Das")
    email: Optional[EmailStr] = Field(None, example="sruti@gmail.com")
    # -------- NURSE PROFILE --------
    nurse_type: str = Field(
        ...,
        example="GNM",
        description="GNM | ANM | CARETAKER | PHYSIO | COMBO"
    )
    aadhaar_number: Optional[str] = Field(
        None,
        example="123412341234"
    )
    qualification_docs: List[str] = Field(
        default_factory=list,
        example=["uploads/documents/gnm_certificate.pdf"]
    )
    experience_docs: List[str] = Field(
        default_factory=list,
        example=["uploads/documents/experience_2yrs.pdf"]
    )
    profile_photo: Optional[str] = Field(
        None,
        example="uploads/nurses/profile.jpg"
    )
    digital_signature: Optional[str] = Field(
        None,
        example="uploads/signatures/sign.png"
    )
    joining_date: Optional[date] = Field(
        None,
        example="2026-01-07"
    )
    resignation_date: Optional[date] = Field(
        None,
        example="2027-01-07"
    )
    shift_type: str = Field(
        ...,
        example="DAY",
        description="DAY | NIGHT | 24_HOURS"
    )

    duty_hours: int = Field(
        ...,
        example=8,
        description="Total duty hours per shift"
    )

    salary_type: str = Field(
        ...,
        example="MONTHLY",
        description="DAILY | MONTHLY"
    )

    salary_amount: float = Field(
        ...,
        example=15000
    )

    payment_mode: str = Field(
        ...,
        example="BANK",
        description="CASH | BANK | UPI"
    )

    salary_date: int = Field(
        ...,
        example=5,
        description="Salary credit date (1–31)"
    )

class NurseResponse(BaseModel):
    nurse_id: str
    user_id: str
    verification_status: str
router = APIRouter(prefix="/nurse", tags=["Nurse"])


@router.post("/create", response_model=NurseResponse)
def create_nurse(payload: NurseCreateRequest):

    if User.objects(phone=payload.phone).first():
        raise HTTPException(400, "Phone number already registered")

    user = User(
        role="NURSE",
        phone=payload.phone,
        email=payload.email,
        is_active=True,
        name=payload.name,
        father_name=payload.father_name
    ).save()

    nurse = NurseProfile(
        user=user,
        nurse_type=payload.nurse_type,
        aadhaar_number=payload.aadhaar_number,
        qualification_docs=payload.qualification_docs,
        experience_docs=payload.experience_docs,
        profile_photo=payload.profile_photo,
        digital_signature=payload.digital_signature,
        joining_date=payload.joining_date,
        resignation_date=payload.resignation_date,
        verification_status="PENDING",
        police_verification_status="PENDING"
    ).save()


    # 🔥 AUTO CREATE PENDING CONSENT
    NurseConsent(
        nurse=nurse,

        shift_type=payload.shift_type,
        duty_hours=payload.duty_hours,

        salary_type=payload.salary_type,
        salary_amount=payload.salary_amount,
        payment_mode=payload.payment_mode,
        salary_date=payload.salary_date,

        status="PENDING",
        created_at=datetime.utcnow()
    ).save()

    return NurseResponse(
        nurse_id=str(nurse.id),
        user_id=str(user.id),
        verification_status=nurse.verification_status
    )

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
@router.get("/duty/status")
def duty_status(user=Depends(get_current_user)):
    nurse = NurseProfile.objects(user=user).first()
    duty = NurseDuty.objects(nurse=nurse).order_by("-created_at").first()

    if not duty:
        return {
            "can_punch_in": True,
            "can_punch_out": False,
        }

    if duty.check_in and not duty.check_out:
        return {
            "can_punch_in": False,
            "can_punch_out": True,
        }

    if duty.check_out:
        return {
            "can_punch_in": True,
            "can_punch_out": False,
        }


@router.post("/visit")
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
@router.get("/patients")
def get_nurse_patients(user=Depends(get_current_user)):

    # 1️⃣ Role check
    if user.role != "NURSE":
        raise HTTPException(status_code=403, detail="Access denied")

    # 2️⃣ Nurse profile
    nurse = NurseProfile.objects(user=user).first()
    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    patients_map = {}

    # 3️⃣ ACTIVE DUTIES (PRIMARY SOURCE)
    duties = NurseDuty.objects(
        nurse=nurse,
        is_active=True
    )

    for duty in duties:
        patient = duty.patient
        if not patient:
            continue

        patient_user = patient.user

        patients_map[str(patient.id)] = {
            "patient_id": str(patient.id),
            "name": patient_user.email.split("@")[0].title() if patient_user and patient_user.email else None,
            "phone": patient_user.phone if patient_user else None,
            "age": patient.age,
            "gender": patient.gender,
            "ward": duty.shift,        # optional mapping
            "room_no": duty.duty_type, # optional mapping
            "source": "DUTY",
            "active": True
        }

    # 4️⃣ VISITS (SECONDARY SOURCE – if no active duty)
    visits = NurseVisit.objects(nurse=nurse)

    for visit in visits:
        patient = visit.patient
        if not patient:
            continue

        pid = str(patient.id)
        if pid in patients_map:
            continue  # already added from duty

        patient_user = patient.user

        patients_map[pid] = {
            "patient_id": pid,
            "name": patient_user.email.split("@")[0].title() if patient_user and patient_user.email else None,
            "phone": patient_user.phone if patient_user else None,
            "age": patient.age,
            "gender": patient.gender,
            "ward": visit.ward,
            "room_no": visit.room_no,
            "source": "VISIT",
            "active": False
        }

    # 5️⃣ Final response
    return {
        "count": len(patients_map),
        "patients": list(patients_map.values())
    }


@router.get("/patients/{patient_id}")
def get_patient_dashboard(patient_id: str, user=Depends(get_current_user)):

    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    patient_user = patient.user

    return {
        "patient_id": str(patient.id),
        "name": patient_user.email.split("@")[0] if patient_user.email else "",
        "age": patient.age,
        "gender": patient.gender,
        "medical_history": patient.medical_history,
    }
@router.post("/patients/{patient_id}/vitals")
def create_vitals(
    patient_id: str,
    bp: str,
    pulse: int,
    spo2: int,
    temperature: float,
    sugar: float = None,
    user=Depends(get_current_user)
):
    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    PatientVitals(
        patient=patient,
        bp=bp,
        pulse=pulse,
        spo2=spo2,
        temperature=temperature,
        sugar=sugar,
        recorded_at=datetime.utcnow()
    ).save()

    return {"message": "Vitals saved successfully"}
@router.post("/patients/{patient_id}/notes")
def add_daily_note(
    patient_id: str,
    note: str,
    user=Depends(get_current_user)
):
    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    nurse = NurseProfile.objects(user=user).first()
    patient = PatientProfile.objects(id=patient_id).first()

    if not nurse or not patient:
        raise HTTPException(404, "Invalid nurse or patient")

    PatientDailyNote(
        patient=patient,
        nurse=nurse,
        note=note,
        created_at=datetime.utcnow()
    ).save()

    return {"message": "Note saved"}

@router.get("/patients/{patient_id}/notes")
def get_notes(patient_id: str, user=Depends(get_current_user)):

    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    notes = PatientDailyNote.objects(
        patient=patient_id
    ).order_by("-created_at")

    return [
        {
            "note": n.note,
            "created_at": n.created_at
        }
        for n in notes
    ]
@router.get("/patients/{patient_id}/medications")
def get_medications(patient_id: str, user=Depends(get_current_user)):

    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    meds = PatientMedication.objects(patient=patient_id)

    return [
        {
            "medicine": m.medicine_name,
            "dosage": m.dosage,
            "timing": m.timing,
            "duration_days": m.duration_days
        }
        for m in meds
    ]
@router.get("/visitsss")
def list_visits(user=Depends(get_current_user)):

    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    nurse = NurseProfile.objects(user=user).first()
    visits = NurseVisit.objects(nurse=nurse).order_by("-visit_time")

    return [
        {
            "visit_id": str(v.id),
            "patient_name": v.patient.user.email.split("@")[0],
            "address": f"Ward {v.ward}, Room {v.room_no}",
            "visit_time": v.visit_time,
            "completed": bool(v.notes)
        }
        for v in visits
    ]
@router.post("/visits/{visit_id}/complete")
def complete_visit(
    visit_id: str,
    notes: str = "Visit completed",
    user=Depends(get_current_user)
):
    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    nurse = NurseProfile.objects(user=user).first()
    visit = NurseVisit.objects(id=visit_id, nurse=nurse).first()

    if not visit:
        raise HTTPException(404, "Visit not found")

    if visit.notes:
        raise HTTPException(400, "Visit already completed")

    visit.notes = notes
    visit.save()

    return {"message": "Visit marked completed"}

@router.get("/attendance")
def nurse_month_attendance(
    month: str = None,   # YYYY-MM
    user=Depends(get_current_user)
):
    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    nurse = NurseProfile.objects(user=user).first()
    if not nurse:
        raise HTTPException(404, "Nurse profile not found")

    today = date.today()

    if month:
        year, mon = map(int, month.split("-"))
        start_date = date(year, mon, 1)
    else:
        start_date = date(today.year, today.month, 1)

    _, last_day = cal.monthrange(start_date.year, start_date.month)

    # 🔥 IMPORTANT FIX: limit till today if current month
    if start_date.year == today.year and start_date.month == today.month:
        max_day = today.day
    else:
        max_day = last_day

    records = NurseAttendance.objects(
        nurse=nurse,
        date__gte=start_date,
        date__lte=date(start_date.year, start_date.month, max_day)
    )

    record_map = {r.date: r for r in records}

    daily = []
    present = absent = half = 0

    for d in range(1, max_day + 1):
        curr_date = date(start_date.year, start_date.month, d)
        rec = record_map.get(curr_date)

        status = "ABSENT"

        if rec and rec.check_in:
            if rec.check_out:
                hours = (rec.check_out - rec.check_in).total_seconds() / 3600
                if hours >= 8:
                    status = "PRESENT"
                    present += 1
                elif hours >= 4:
                    status = "HALF"
                    half += 1
                else:
                    absent += 1
            else:
                status = "HALF"
                half += 1
        else:
            absent += 1

        daily.append({
            "day": d,
            "date": curr_date.isoformat(),
            "status": status
        })

    return {
        "month": start_date.strftime("%Y-%m"),
        "summary": {
            "present": present,
            "absent": absent,
            "half": half
        },
        "attendance": daily
    }
class NurseConsentSignRequest(BaseModel):
    confidentiality_accepted: bool
    no_direct_payment_accepted: bool
    police_termination_accepted: bool
    signature_image: Optional[str]

@router.post("/consent/sign")
def sign_consent(
    payload: NurseConsentSignRequest,
    user=Depends(get_current_user)
):
    # 🔐 Role check
    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    nurse = NurseProfile.objects(user=user).first()
    if not nurse:
        raise HTTPException(404, "Nurse profile not found")

    # ❌ Already signed check
    already_signed = NurseConsent.objects(
        nurse=nurse,
        status="SIGNED"
    ).first()

    if already_signed:
        raise HTTPException(400, "Consent already signed")

    # ✅ Get pending consent
    consent = NurseConsent.objects(
        nurse=nurse,
        status="PENDING"
    ).first()

    if not consent:
        raise HTTPException(404, "No pending consent found")

    # ❌ Checkbox validation
    if not (
        payload.confidentiality_accepted and
        payload.no_direct_payment_accepted and
        payload.police_termination_accepted
    ):
        raise HTTPException(400, "All checkboxes must be accepted")

    # ✅ Update consent
    consent.confidentiality_accepted = True
    consent.no_direct_payment_accepted = True
    consent.police_termination_accepted = True
    consent.signature_image = payload.signature_image
    consent.status = "SIGNED"
    consent.signed_at = datetime.utcnow()   # 🔥 better than overwriting created_at
    consent.save()

    return {
        "message": "Consent signed successfully",
        "status": consent.status
    }


@router.get("/consent/status")
def consent_status(user=Depends(get_current_user)):

    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    nurse = NurseProfile.objects(user=user).first()
    consent = NurseConsent.objects(nurse=nurse).first()

    if not consent or consent.status != "SIGNED":
        return {
            "signed": False,
            "status": "NOT_SIGNED"
        }

    return {
        "signed": True,
        "status": consent.status,
        "signed_at": consent.created_at
    }

