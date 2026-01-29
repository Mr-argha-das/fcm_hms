
from collections import defaultdict
from urllib import request
from fastapi import APIRouter, Depends, HTTPException, Request,status
from datetime import datetime, timedelta,date
from mongoengine.errors import ValidationError, NotUniqueError
from bson import ObjectId


from core.dependencies import get_current_user
from models import (
    AboutUs, DoctorProfile, NurseLiveLocation, NurseProfile, NurseDuty, NurseAttendance,
    NurseSalary, NurseConsent, NurseVisit, PatientProfile, User, PatientVitals, PatientDailyNote, PatientMedication
)

from routes.auth.schemas import NurseConsentRequest, NurseVisitCreate
from .utils import ensure_consent_active, ensure_duty_time
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import date

import traceback
from zoneinfo import ZoneInfo
import calendar 
from core.utils.files import with_domain

IST = ZoneInfo("Asia/Kolkata")

def ist_now():
    return datetime.now(IST)

# BASE_URL = "https://wecarehhcs.in"

# def with_domain(path: str | None):
#     if not path:
#         return None
#     if path.startswith("http"):
#         return path
#     return f"{BASE_URL}{path}"

class NurseCreateRequest(BaseModel):
    phone: str = Field(..., example="9876543210")
    other_number: str = Field(..., example="9876543210")
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
    addhar_front: Optional[str] = Field(    
        None,
        example="uploads/documents/aadhaar_front.jpg"
    )
    aadhaar_back: Optional[str] = Field(    
        None,
        example="uploads/documents/aadhaar_back.jpg"
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

class NurseSelfSignupRequest(BaseModel):
    # -------- USER --------
    phone: str = Field(..., example="9876543210")
    other_number: str = Field(..., example="9876543210")
    name: str = Field(..., example="Sruti Das")
    father_name: Optional[str] = Field(None, example="Ram Das")
    email: Optional[EmailStr] = Field(None, example="sruti@gmail.com")
    # -------- NURSE PROFILE --------
    nurse_type: str = Field(
        ...,
        example="GNM",
        description="GNM | ANM | CARETAKER | PHYSIO | COMBO"
    )
    aadhaar_number: Optional[str] = None
    aadhaar_front: Optional[str] = None
    aadhaar_back: Optional[str] = None
    qualification_docs: List[str] = Field(default_factory=list)
    experience_docs: List[str] = Field(default_factory=list)
    profile_photo: Optional[str] = None
    digital_signature: Optional[str] = None
    joining_date: Optional[date] = None



@router.get("/about-us-get")
def get_about_us():
    about = AboutUs.objects.first()
    # print(about.to_json())
    # 🔥 if no data → return default empty
    if not about:
        return {
            "id": None,
            "name": "",
            "designation": "",
            "description": "",
            "profile_image": "",
        }

    return {
        "id": str(about.id),
        "name": about.name,
        "designation": about.designation,
        "description": about.description,
        "profile_image": with_domain(about.profile_image),
    }


@router.post("/self-signup", response_model=NurseResponse)
def nurse_self_signup(payload: NurseSelfSignupRequest):

    # ❌ Duplicate check
    if User.objects(phone=payload.phone).first():
        raise HTTPException(400, "Phone number already registered")

    # 1️⃣ Create USER
    user = User(
        role="NURSE",
        phone=payload.phone,
        other_number=payload.other_number,
        email=payload.email,
        name=payload.name,
        father_name=payload.father_name,
        is_active=False,          # 🔥 ADMIN approval needed
        otp_verified=False
    ).save()

    # 2️⃣ Create NURSE PROFILE
    nurse = NurseProfile(
        user=user,
        nurse_type=payload.nurse_type,
        aadhaar_front=payload.aadhaar_front,
        aadhaar_back=payload.aadhaar_back,
        qualification_docs=payload.qualification_docs,
        experience_docs=payload.experience_docs,
        profile_photo=payload.profile_photo,
        digital_signature=payload.digital_signature,
        joining_date=payload.joining_date,
        verification_status="PENDING",
        police_verification_status="PENDING",
        created_by="SELF"
    ).save()

    return NurseResponse(
        nurse_id=str(nurse.id),
        user_id=str(user.id),
        verification_status=nurse.verification_status
    )


# 
@router.get("/self-signup/me", response_model=NurseSelfSignupRequest)
def get_my_profile(current_user: User = Depends(get_current_user)):

    nurse = NurseProfile.objects(user=current_user).first()
    if not nurse:
        raise HTTPException(404, "Profile not found")

    return {
        # USER
        "phone": current_user.phone,
        "other_number": current_user.other_number,
        "name": current_user.name,
        "father_name": current_user.father_name,
        "email": current_user.email,

        # PROFILE
        "nurse_type": nurse.nurse_type,
        "aadhaar_number": nurse.aadhaar_number,
        "qualification_docs": nurse.qualification_docs,
        "experience_docs": nurse.experience_docs,
        "profile_photo": nurse.profile_photo,
        "digital_signature": nurse.digital_signature,
        "joining_date": nurse.joining_date,
    }

@router.put("/self-signup/update")
def update_my_profile(
    payload: NurseSelfSignupRequest,
    current_user: User = Depends(get_current_user)
): 
    nurse = NurseProfile.objects(user=current_user).first()
    if not nurse:
       raise HTTPException(404, "Profile not found")

    # 🔹 update user
    current_user.update(
        set__phone=payload.phone,
        set__other_number=payload.other_number,
        set__name=payload.name,
        set__father_name=payload.father_name,
        set__email=payload.email,
    )

    # 🔹 update nurse
    nurse.update(
        set__nurse_type=payload.nurse_type,
        set__aadhaar_number=payload.aadhaar_number,
        set__qualification_docs=payload.qualification_docs,
        set__experience_docs=payload.experience_docs,
        set__profile_photo=payload.profile_photo,
        set__digital_signature=payload.digital_signature,
        set__joining_date=payload.joining_date,
    )
    
    return {"message": "Profile updated successfully"}
    
class SignatureUpdateSchema(BaseModel):
    signature_path: str

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


@router.post("/create", response_model=NurseResponse)
async def create_nurse(payload: NurseCreateRequest , request: Request):   
    print(payload)     
    raw_body = await request.body()
    print("🔵 RAW REQUEST BODY:", raw_body)
    try:
        # 🔍 RAW BODY (as sent by client)

        # 🔍 Parsed payload (after Pydantic validation)
        # print("🟢 PARSED PAYLOAD:", payload.dict())

        # 🔹 Duplicate phone check
        if User.objects(phone=payload.phone).first():
            raise HTTPException(status_code=400, detail="Phone number already registered")
        

        # 🔹 Create User
        user = User(
            role="NURSE",
            phone=payload.phone,
            other_number=payload.other_number,
            email=payload.email,
            name=payload.name,
            father_name=payload.father_name,
            is_active=True,
            otp_verified=True
        ).save()


        # 🔹 Create Nurse Profile
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
            created_by="ADMIN"
        ).save()

        # 🔹 Auto create Nurse Consent
        NurseConsent(
            nurse=nurse,
            shift_type=payload.shift_type,
            duty_hours=payload.duty_hours,
            salary_type=payload.salary_type,
            salary_amount=payload.salary_amount,
            payment_mode=payload.payment_mode,
            salary_date=payload.salary_date
        ).save()

        # ✅ Success response
        return NurseResponse(
            nurse_id=str(nurse.id),
            user_id=str(user.id),
            verification_status=nurse.verification_status
        )

    # 🔴 MongoEngine validation error
    except ValidationError as e:
        print("ValidationError:", e)
        raise HTTPException(status_code=400, detail=str(e))

    # 🔴 Unique key error (phone / email etc.)
    except NotUniqueError as e:
        print("NotUniqueError:", e)
        raise HTTPException(status_code=400, detail="Duplicate data error")

    # 🔴 FastAPI raised error (re-throw)
    except HTTPException as e:
        raise e

    # 🔴 Any unknown crash (VERY IMPORTANT)
    except Exception as e:
        print("Unhandled Exception:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Internal server error while creating nurse"
        )


@router.delete("/delete/{nurse_id}")
def delete_nurse(
    nurse_id: str,
):
    try:
        nurse = NurseProfile.objects(id=nurse_id).first()
        if not nurse:
            raise HTTPException(status_code=404, detail="Nurse not found")

        user = nurse.user

        # 🔥 DELETE RELATED DATA (ORDER MATTERS)
        NurseConsent.objects(nurse=nurse).delete()
        NurseDuty.objects(nurse=nurse).delete()
        NurseAttendance.objects(nurse=nurse).delete()
        NurseVisit.objects(nurse=nurse).delete()

        # 🔥 DELETE NURSE PROFILE
        nurse.delete()

        # 🔥 DELETE USER ACCOUNT
        if user:
            user.delete()

        return {
            "success": True,
            "message": "Nurse deleted successfully"
        }

    except Exception as e:
        print("❌ Delete nurse error:", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete nurse"
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
    if not nurse:
        raise HTTPException(404, "Nurse not found")

    if nurse.police_verification_status == "FAILED":
        raise HTTPException(403, "Police verification failed")


    now = datetime.now(IST)

    # prevent double check-in
    existing = NurseAttendance.objects(
        nurse=nurse,
        date=now.date()
    ).first()

    if existing and existing.check_in:
        raise HTTPException(400, "Already checked in today")

    NurseAttendance(
        nurse=nurse,
        date=now.date(),
        check_in=now,
        method="FACE"
    ).save()

    return {
        "message": "Checked in successfully",
        "check_in_time": now.isoformat()
    }
@router.post("/duty/check-out")
def duty_check_out(user=Depends(get_current_user)):
    nurse = NurseProfile.objects(user=user).first()
    if not nurse:
        raise HTTPException(404, "Nurse not found")

    now = datetime.now(IST)

    



    # duty update
  

    # attendance update
    attendance = NurseAttendance.objects(
        nurse=nurse,
        date=now.date()
    ).first()

    if attendance:
        attendance.check_out = now
        attendance.save()

    return {
        "message": "Checked out successfully",
        "check_out_time": now.isoformat()
    }

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
    
    return {
            "can_punch_in": True,
            "can_punch_out": True,
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
            "patient_name": patient_user.name if patient_user else None,
            "ward": v.ward,
            "room_no": v.room_no,
            "address": v.address,
            "dutyLocation": v.dutyLocation,
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
           "profile": with_domain(nurse.profile_photo) if nurse.profile_photo else "/static/default.png",
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


# Location Track
@router.post("/location/update")
def update_location(
    payload: dict,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "NURSE":
        raise HTTPException(403, "Only nurse allowed")

    nurse = NurseProfile.objects(user=current_user).first()
    if not nurse:
        raise HTTPException(404, "Nurse not found")

    NurseLiveLocation.objects(nurse=nurse).update_one(
        set__latitude=payload["latitude"],
        set__longitude=payload["longitude"],
        set__updated_at=datetime.utcnow(),
        upsert=True
    )

    return {"success": True}

@router.get("/{nurse_id}/location-track")
def get_nurse_location(nurse_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(403)

    loc = NurseLiveLocation.objects(
        nurse=nurse_id
    ).first()

    if not loc:
        return {"active": False}

    return {
        "active": True,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "updated_at": loc.updated_at
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


# class VitalsPayload(BaseModel):
#     bp: str
#     pulse: int
#     spo2: int
#     temperature: float
#     sugar: Optional[float] = None


# @router.post("/patients/{patient_id}/vitals")
# def create_vitals(
#     patient_id: str,
#     payload: VitalsPayload,
#     user=Depends(get_current_user)
# ):
#     if user.role != "NURSE":
#         raise HTTPException(403, "Access denied")

#     patient = PatientProfile.objects(id=patient_id).first()
#     if not patient:
#         raise HTTPException(404, "Patient not found")

#     PatientVitals(
#         patient=patient,
#         bp=payload.bp,
#         pulse=payload.pulse,
#         spo2=payload.spo2,
#         temperature=payload.temperature,
#         sugar=payload.sugar,
#         recorded_at=datetime.utcnow()
#     ).save()

#     return {"message": "Vitals saved successfully"}

class VitalsPayload(BaseModel):
    # 🔹 BASIC
    bp: str
    pulse: int
    spo2: int
    temperature: float
    o2_level: Optional[int] = None
    rbs: Optional[float] = None

    # 🔹 SUPPORT
    bipap_ventilator: Optional[str] = None
    iv_fluids: Optional[str] = None
    suction: Optional[str] = None
    feeding_tube: Optional[str] = None

    # 🔹 OUTPUT
    vomit_aspirate: Optional[str] = None
    urine: Optional[str] = None
    stool: Optional[str] = None

    # 🔹 NOTES
    other: Optional[str] = None
    
class DailyNotePayload(BaseModel):
    note: str


@router.post("/patients/{patient_id}/vital-details")
def create_vitals(
    patient_id: str,
    payload: VitalsPayload,
    user=Depends(get_current_user)
):
    print("🔥 CREATE VITALS PAYLOAD:", payload.dict())
    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    vitals = PatientVitals(
        patient=patient,

        # 🔹 BASIC
        bp=payload.bp,
        pulse=payload.pulse,
        spo2=payload.spo2,
        temperature=payload.temperature,
        o2_level=payload.o2_level,
        rbs=payload.rbs,

        # 🔹 SUPPORT
        bipap_ventilator=payload.bipap_ventilator,
        iv_fluids=payload.iv_fluids,
        suction=payload.suction,
        feeding_tube=payload.feeding_tube,

        # 🔹 OUTPUT
        vomit_aspirate=payload.vomit_aspirate,
        urine=payload.urine,
        stool=payload.stool,

        # 🔹 NOTES
        other=payload.other,

        recorded_at=datetime.utcnow()
    )

    vitals.save()

    return {
        "success": True,
        "message": "Vitals saved successfully"
    }

# =====================================================
# GET VITALS (History)
# =====================================================

@router.get("/patients/{patient_id}/vital-details")
def get_vitals(
    patient_id: str,
    limit: int = 20,
    user=Depends(get_current_user)
):
    print("📥 GET VITALS HIT:", patient_id, "limit:", limit)

    # 🔒 Only nurse allowed
    if user.role != "NURSE":
        raise HTTPException(status_code=403, detail="Access denied")

    # 🔥 safe limit (avoid huge DB load)
    limit = max(1, min(limit, 100))

    # 🔍 patient check
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # 🔥 latest first
    vitals_qs = (
        PatientVitals.objects(patient=patient)
        .order_by("-recorded_at")
        .limit(limit)
    )

    vitals_list = []

    for v in vitals_qs:
        vitals_list.append({
            "id": str(v.id),
            
            # 🔹 BASIC
            "bp": v.bp,
            "pulse": v.pulse,
            "spo2": v.spo2,
            "temperature": v.temperature,
            "o2_level": v.o2_level,
            "rbs": v.rbs,
            
            # 🔹 SUPPORT / DEVICES
            "bipap_ventilator": v.bipap_ventilator,
            "iv_fluids": v.iv_fluids,
            "suction": v.suction,
            "feeding_tube": v.feeding_tube,

            # 🔹 OUTPUTS
            "vomit_aspirate": v.vomit_aspirate,
            "urine": v.urine,
            "stool": v.stool,

            # 🔹 NOTES
            "other": v.other,

            # 🔹 META
            "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None
        })

    print("✅ Returning vitals count:", len(vitals_list))

    return {
        "success": True,
        "count": len(vitals_list),
        "vitals": vitals_list
    }


@router.post("/patients/{patient_id}/notes")
def add_daily_note(
    patient_id: str,
    payload: DailyNotePayload,
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
        note=payload.note,
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


# @router.get("/nurse/visits")
# def nurse_visits(
#     request: Request,
#     current_user: User = Depends(get_current_user)
# ):
#     if current_user.role != "NURSE":
#         raise HTTPException(403, "Unauthorized")

#     nurse = NurseProfile.objects(user=current_user).first()
#     if not nurse:
#         raise HTTPException(404, "Nurse profile not found")

#     # 🔥 Pending first
#     pending_visits = NurseVisit.objects(
#         nurse=nurse,
#         notes__in=[None, ""]
#     ).order_by("-visit_time")

#     # 🔥 Completed later
#     completed_visits = NurseVisit.objects(
#         nurse=nurse,
#         notes__nin=[None, ""]
#     ).order_by("-visit_time")

#     visits = list(pending_visits) + list(completed_visits)
    
#     data = []

#     for v in visits:
#         patient = v.patient

#         # 🔹 MEDICATIONS for this patient
#         meds = []
#         if patient:
#             medications = PatientMedication.objects(patient=patient)
#             for m in medications:
#                 meds.append({
#                     "medicine_name": m.medicine_name,
#                     "dosage": m.dosage,
#                     "timing": m.timing,
#                     "duration_days": m.duration_days
#                 })

#         data.append({
#             "visit_id": str(v.id),

#             # PATIENT
#             "patient_id": str(patient.id) if patient else None,
#             "patient_name": patient.user.name if patient else "Unknown",
#             "address": patient.address if patient else "",

#             # VISIT
#             "visit_type": v.visit_type,
#             "visit_time": v.visit_time.isoformat(),
#             "completed": bool(v.notes),

#             # LOCATION
#             "ward": v.ward,
#             "room_no": v.room_no,

#             # 💊 MEDICATIONS
#             "medications": meds
#         })

#     return data


@router.get("/nurse/visits")
def nurse_visits(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "NURSE":
        raise HTTPException(403, "Unauthorized")

    nurse = NurseProfile.objects(user=current_user).first()
    if not nurse:
        raise HTTPException(404, "Nurse profile not found")

    # 🔥 Pending first
    pending_visits = NurseVisit.objects(
        nurse=nurse,
        notes__in=[None, ""]
    ).order_by("-visit_time")

    # 🔥 Completed later
    completed_visits = NurseVisit.objects(
        nurse=nurse,
        notes__nin=[None, ""]
    ).order_by("-visit_time")

    visits = list(pending_visits) + list(completed_visits)
    
    data = []

    for v in visits:
        patient = v.patient

        # 💊 MEDICATIONS
        meds = []
        if patient:
            medications = PatientMedication.objects(patient=patient)
            for m in medications:
                meds.append({
                    "medicine_name": m.medicine_name,
                    "dosage": m.dosage,
                    "timing": m.timing,
                    "duration_days": m.duration_days
                })

        # 📍 LOCATION LOGIC
        location_data = {
            "dutyLocation": v.dutyLocation
        }

        if v.dutyLocation == "HOSPITAL":
            location_data.update({
                "ward": v.ward,
                "room_no": v.room_no,
                "address": None
            })
        else:  # HOME
            location_data.update({
                "ward": None,
                "room_no": None,
                "address": v.address
            })

        data.append({
            "visit_id": str(v.id),

            # 👤 PATIENT
            "patient_id": str(patient.id) if patient else None,
            "patient_name": patient.user.name if patient else "Unknown",
            "patient_address": patient.address if patient else "",

            # 🕒 VISIT
            "visit_type": v.visit_type,
            "visit_time": v.visit_time.isoformat(),
            "completed": bool(v.notes),

            # 📍 LOCATION
            **location_data,

            # 💊 MEDICATIONS
            "medications": meds
        })

    return data


# Create Vist Admin Schema
class NurseVisitCreateAdmin(BaseModel):
    nurse_id: str
    patient_id: str
    duty_id: Optional[str] = None

    dutyLocation: str   # HOME / HOSPITAL

    ward: Optional[str] = None
    room_no: Optional[str] = None
    address: Optional[str] = None

    visit_type: str
    notes: Optional[str] = None

@router.post("/visit/create-admin")
def create_visit_admin(
    payload: NurseVisitCreateAdmin,
    current_user: User = Depends(get_current_user)
):
    print("🔥 ADMIN VISIT CREATE HIT")

    if current_user.role != "ADMIN":
        raise HTTPException(403, "Only admin allowed")

    nurse = NurseProfile.objects(id=payload.nurse_id).first()
    if not nurse:
        raise HTTPException(404, "Nurse not found")

    patient = PatientProfile.objects(id=payload.patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # 🔐 LOCATION VALIDATION
    if payload.dutyLocation == "HOME":
        if not payload.address:
            raise HTTPException(
                400, "Address is required for HOME visit"
            )

        # hospital fields ignore
        ward = None
        room_no = None

    elif payload.dutyLocation == "HOSPITAL":
        ward = payload.ward
        room_no = payload.room_no
        address = None

    else:
        raise HTTPException(400, "Invalid dutyLocation")

    visit = NurseVisit(
        nurse=nurse,
        patient=patient,
        duty=payload.duty_id,
        dutyLocation=payload.dutyLocation,
        ward=ward,
        room_no=room_no,
        address=payload.address if payload.dutyLocation == "HOME" else None,
        visit_type=payload.visit_type,
        notes=payload.notes,
        created_by=current_user
    )

    visit.save()

    return {
        "success": True,
        "message": "Visit created successfully",
        "visit_id": str(visit.id)
    }


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

import calendar as cal


@router.get("/attendance")
def nurse_month_attendance(
    month: str | None = None,   # format: YYYY-MM
    user=Depends(get_current_user)
):
    # -----------------------------
    # 🔐 Role check
    # -----------------------------
    if user.role != "NURSE":
        raise HTTPException(status_code=403, detail="Access denied")

    nurse = NurseProfile.objects(user=user).first()
    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")

    today = date.today()

    # -----------------------------
    # 📅 Month handling
    # -----------------------------
    try:
        if month:
            year, mon = map(int, month.split("-"))
            start_date = date(year, mon, 1)
        else:
            start_date = date(today.year, today.month, 1)
    except:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")

    _, last_day = cal.monthrange(start_date.year, start_date.month)

    # limit till today for current month
    max_day = today.day if (
        start_date.year == today.year and
        start_date.month == today.month
    ) else last_day

    end_date = date(start_date.year, start_date.month, max_day)

    # -----------------------------
    # 📦 Fetch records
    # -----------------------------
    records = NurseAttendance.objects(
        nurse=nurse,
        date__gte=start_date,
        date__lte=end_date
    )

    # 🔥 IMPORTANT: normalize date (fixes your bug)
    record_map = {
        (r.date.date() if hasattr(r.date, "date") else r.date): r
        for r in records
    }

    daily = []
    present = 0
    absent = 0
    half = 0

    # -----------------------------
    # 🧠 Status calculation
    # -----------------------------
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
                    status = "ABSENT"
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

    # -----------------------------
    # ✅ Response
    # -----------------------------
    return {
        "month": start_date.strftime("%Y-%m"),
        "summary": {
            "present": present,
            "half": half,
            "absent": absent,
            "total_days": max_day
        },
        "attendance": daily
    }


# @router.get("/attendance")
# def nurse_month_attendance(
#     month: str = None,   # YYYY-MM
#     user=Depends(get_current_user)
# ):
#     if user.role != "NURSE":
#         raise HTTPException(403, "Access denied")

#     nurse = NurseProfile.objects(user=user).first()
#     if not nurse:
#         raise HTTPException(404, "Nurse profile not found")

#     today = date.today()

#     if month:
#         year, mon = map(int, month.split("-"))
#         start_date = date(year, mon, 1)
#     else:
#         start_date = date(today.year, today.month, 1)

#     _, last_day = cal.monthrange(start_date.year, start_date.month)

#     # 🔥 IMPORTANT FIX: limit till today if current month
#     if start_date.year == today.year and start_date.month == today.month:
#         max_day = today.day
#     else:
#         max_day = last_day

#     records = NurseAttendance.objects(
#         nurse=nurse,
#         date__gte=start_date,
#         date__lte=date(start_date.year, start_date.month, max_day)
#     )

#     record_map = {r.date: r for r in records}

#     daily = []
#     present = absent = half = 0

#     for d in range(1, max_day + 1):
#         curr_date = date(start_date.year, start_date.month, d)
#         rec = record_map.get(curr_date)

#         status = "ABSENT"

#         if rec and rec.check_in:
#             if rec.check_out:
#                 hours = (rec.check_out - rec.check_in).total_seconds() / 3600
#                 if hours >= 8:
#                     status = "PRESENT"
#                     present += 1
#                 elif hours >= 4:
#                     status = "HALF"
#                     half += 1
#                 else:
#                     absent += 1
#             else:
#                 status = "HALF"
#                 half += 1
#         else:
#             absent += 1

#         daily.append({
#             "day": d,
#             "date": curr_date.isoformat(),
#             "status": status
#         })

#     return {
#         "month": start_date.strftime("%Y-%m"),
#         "summary": {
#             "present": present,
#             "absent": absent,
#             "half": half
#         },
#         "attendance": daily
#     }



class NurseConsentSignRequest(BaseModel):
    signature_image: str  



@router.post("/consent/sign")
def sign_consent(
    payload: NurseConsentSignRequest,
    user=Depends(get_current_user)
):
    # 🔒 Only nurse can sign
    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    nurse = NurseProfile.objects(user=user).first()
    if not nurse:
        raise HTTPException(404, "Nurse profile not found")

    # ❌ Already signed check
    existing = NurseConsent.objects(nurse=nurse, status="SIGNED").first()
    if existing:
        raise HTTPException(400, "Consent already signed")

    # ✅ Get pending consent
    consent = NurseConsent.objects(nurse=nurse, status="PENDING").first()
    if not consent:
        raise HTTPException(404, "No pending consent found")

    # ✅ Save signature and mark consent as signed
    consent.signature_image = payload.signature_image
    consent.status = "SIGNED"
    consent.signed_at = datetime.utcnow()
    consent.save()

    return {
        "message": "Consent signed successfully",
        "status": consent.status,
        "signed_at": consent.signed_at,
        "signature_image": consent.signature_image
    }


@router.get("/consent/status")
def consent_status(user=Depends(get_current_user)):

    # 🔒 Only nurses allowed
    if user.role != "NURSE":
        raise HTTPException(403, "Access denied")

    nurse = NurseProfile.objects(user=user).first()
    if not nurse:
        raise HTTPException(404, "Nurse profile not found")

    consent = NurseConsent.objects(nurse=nurse).first()

    # ❌ Condition 1: Consent must exist and be SIGNED
    if not consent or consent.status != "SIGNED":
        return {
            "signed": False,
            "reason": "CONSENT_NOT_SIGNED",
            "police_verified": nurse.police_verification_status,
            "aadhaar_verified": nurse.aadhaar_verified
        }

    # ❌ Condition 2: Police verification must be CLEAR
    if nurse.police_verification_status != "CLEAR":
        return {
            "signed": False,
            "reason": "POLICE_VERIFICATION_PENDING",
            "police_verified": nurse.police_verification_status,
            "aadhaar_verified": nurse.aadhaar_verified
        }

    # ❌ Condition 3: Aadhaar must be verified
    if not nurse.aadhaar_verified:
        return {
            "signed": False,
            "reason": "AADHAAR_NOT_VERIFIED",
            "police_verified": nurse.police_verification_status,
            "aadhaar_verified": nurse.aadhaar_verified
        }

    # ✅ ALL CONDITIONS PASSED
    return {
        "signed": True,
        "status": "SIGNED",
        "signed_at": consent.signed_at,
        "police_verified": "CLEAR",
        "aadhaar_verified": True
    }




# Add Medication for a patient
@router.post("/nurse/{nurse_id}/assign-duty")
def assign_duty(nurse_id: str, payload: dict):
    nurse = NurseProfile.objects(id=nurse_id).first()
    patient = PatientProfile.objects(id=payload["patient_id"]).first()
    if not nurse or not patient:
        raise HTTPException(status_code=404, detail="Nurse or Patient not found")

    duty = NurseDuty(
        nurse=nurse,
        patient=patient,
        duty_type=payload["duty_type"],
        shift=payload["shift"],
        duty_start=datetime.fromisoformat(payload["duty_start"]),
        duty_end=datetime.fromisoformat(payload["duty_end"]),
        is_active=True
    )
    duty.save()
    return {"status": "success", "message": "Duty assigned"}

# Log Visit
@router.post("/nurse/{nurse_id}/log-visit")
def log_visit(nurse_id: str, payload: dict):
    nurse = NurseProfile.objects(id=nurse_id).first()
    patient = PatientProfile.objects(id=payload["patient_id"]).first()
    if not nurse or not patient:
        raise HTTPException(status_code=404, detail="Nurse or Patient not found")

    visit = NurseVisit(
        nurse=nurse,
        patient=patient,
        ward=payload.get("ward"),
        room_no=payload.get("room_no", ""),
        visit_type=payload["visit_type"],
        visit_time=datetime.utcnow(),
        created_by=nurse.user
    )
    visit.save()
    return {"status": "success", "message": "Visit logged"}

@router.get("/profile/me/json")
def my_nurse_profile(current_user=Depends(get_current_user), month: str = None):
    nurse = NurseProfile.objects(user=current_user).first()
    if not nurse:
        raise HTTPException(404, "Nurse profile not found")

    print(nurse.to_mongo())
    user = nurse.user

    if month is None:
        month = datetime.utcnow().strftime("%Y-%m")

    try:
        year, mon = map(int, month.split("-"))
        last_day = calendar.monthrange(year, mon)[1]  # ✅ works now
    except Exception:
        raise HTTPException(400, "Invalid month format. Expected YYYY-MM")

    start_date = date(year, mon, 1)
    end_date = date(year, mon, last_day)

    # ------------------ ATTENDANCE ------------------
    attendance_qs = NurseAttendance.objects(
        nurse=nurse,
        date__gte=start_date,
        date__lte=end_date
    ).order_by("date")

    total_present = attendance_qs.count()
    attendance_map = defaultdict(int)
    for att in attendance_qs:
        attendance_map[att.date.day] += 1

    chart_labels = list(range(1, last_day + 1))
    chart_values = [attendance_map.get(day, 0) for day in chart_labels]

    # ------------------ SALARY ------------------
    salary = NurseSalary.objects(nurse=nurse, month=month).first()

    # ------------------ ACTIVE DUTY ------------------
    active_duty = NurseDuty.objects(nurse=nurse, is_active=True).first()

    # ------------------ RECENT VISITS ------------------
    visits = NurseVisit.objects(nurse=nurse).order_by("-visit_time")[:10]

    # ------------------ CONSENT ------------------
    consent = NurseConsent.objects(nurse=nurse).order_by("-created_at").first()

    # ------------------ RETURN JSON ------------------
    return {
        "nurse": {
            "id": str(nurse.id),
            "phone": user.phone,
            "name" : user.name,
            "nurse_type": nurse.nurse_type,
            "aadhaar_verified": nurse.aadhaar_verified,
            "digital_signature_verify": nurse.digital_signature_verify,

            "verification_status": nurse.verification_status,
            "police_verification_status": nurse.police_verification_status,
            "joining_date": str(nurse.joining_date),
            "resignation_date": str(nurse.resignation_date) if nurse.resignation_date else None,
            # "profile_photo": nurse.profile_photo,
            # "qualification_docs": nurse.qualification_docs,
            # "experience_docs": nurse.experience_docs,
            "profile_photo": with_domain(nurse.profile_photo),
            "qualification_docs": [with_domain(p) for p in nurse.qualification_docs],
            "experience_docs": [with_domain(p) for p in nurse.experience_docs],
              # ✅ NEW FIELDS ADDED
            "digital_signature": with_domain(nurse.digital_signature),
        },

        "kpi": {
            "attendance": total_present,
            "salary": salary.net_salary if salary else None,
            "salary_paid": salary.is_paid if salary else None,
            "active_duty": active_duty.duty_type if active_duty else None,
            "shift": active_duty.shift if active_duty else None,
            "consent_status": consent.status if consent else None,
            "consent_version": consent.version if consent else None
        },
        "attendance_graph": {
            "labels": chart_labels,
            "values": chart_values
        },
        "attendance_records": [
            {
                "date": att.date.strftime("%Y-%m-%d"),
                "check_in": att.check_in.strftime("%H:%M") if att.check_in else None,
                "check_out": att.check_out.strftime("%H:%M") if att.check_out else None,
                "method": att.method
            } for att in attendance_qs
        ],
        "recent_visits": [
            {
                "visit_type": v.visit_type,
                "patient_id": str(v.patient.id),
                "visit_time": v.visit_time.strftime("%Y-%m-%d %H:%M")
            } for v in visits
        ]
    }