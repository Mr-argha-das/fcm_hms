import json
import traceback
from typing import Optional , List
from urllib import request
from datetime import datetime, timedelta,date


from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException ,Request
from core.dependencies import get_current_user
from models import (
    DoctorProfile, EquipmentTable, HospitalModel, Medicine, NurseDuty, NurseProfile, PatientProfile, PatientDailyNote,
    PatientVitals, PatientMedication, RelativeAccess, StaffProfile, User, UserEquipmentRequest
)

from mongoengine.errors import NotUniqueError ,ValidationError
from pydantic import BaseModel, EmailStr
from routes.auth.schemas import EquipmentCreate, EquipmentRequestCreate, EquipmentRequestUpdate, EquipmentUpdate

from zoneinfo import ZoneInfo

router = APIRouter(prefix="/patient", tags=["Patient"])

equipment_router = APIRouter(prefix="/equipment")

class PatientCreateRequest(BaseModel):
    name: str
    phone: str

    father_name: Optional[str] = None
    other_number: Optional[str] = None
    email: Optional[EmailStr] = None

    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    service_start: Optional[date] = None
    service_end: Optional[date] = None

    hospital: Optional[str] = None
    assigned_doctor: Optional[str] = None

    documents: List[str] = []
    assigned_caretaker : Optional[List[str]] = []
    adharcard : Optional[str] = None
       # 🔥 IMPORTANT

@router.post("/create")
async def create_patient(
    payload: PatientCreateRequest,
    request: Request
):
    print("🟢 CREATE PATIENT PAYLOAD:", payload)
    raw_body = await request.body()
    print("🔵 RAW REQUEST BODY:", raw_body)

    try:
        # ❌ duplicate phone check
        if User.objects(phone=payload.phone).first():
            raise HTTPException(
                status_code=400,
                detail="Phone number already registered"
            )

        # 🔹 Create USER
        user = User(
            role="PATIENT",
            name=payload.name,
            father_name=payload.father_name,
            phone=payload.phone,
            password_hash=payload.phone,
            other_number=payload.other_number,
            email=payload.email,
            otp_verified=True,
            is_active=True
        )

        # 🏥 Hospital (safe)
        if payload.hospital:
            user.hospital = HospitalModel.objects.get(
                id=ObjectId(payload.hospital)
            )

        user.save()

        # 🔹 Create PATIENT PROFILE
        patient = PatientProfile(
            user=user,
            age=payload.age,
            gender=payload.gender,
            medical_history=payload.medical_history,
            address=payload.address,
            service_start=payload.service_start,
            service_end=payload.service_end,
            documents=payload.documents or [],
            city=payload.city,
            state=payload.state,
            pincode=payload.pincode,
            assigned_caretaker=[
                NurseProfile.objects.get(id=ObjectId(nurse_id))  for nurse_id in (payload.assigned_caretaker or [])  ],
                adharcard=payload.adharcard
        )

        # 👨‍⚕️ Assign doctor (safe)
        if payload.assigned_doctor:
            patient.assigned_doctor = DoctorProfile.objects.get(
                id=ObjectId(payload.assigned_doctor)
            )

        patient.save()

        return {
            "success": True,
            "patient_id": str(patient.id),
            "user_id": str(user.id)
        }

    # 🔴 Mongo validation error
    except ValidationError as e:
        print("ValidationError:", e)
        raise HTTPException(status_code=400, detail=str(e))

    # 🔴 Duplicate phone/email
    except NotUniqueError:
        raise HTTPException(
            status_code=400,
            detail="Phone already registered"
        )

    # 🔴 FastAPI raised error
    except HTTPException as e:
        raise e

    # 🔴 Unknown crash
    except Exception as e:
        print("Unhandled Exception:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Internal server error while creating patient"
        )

# @router.post("/create")
# def create_patient(payload: dict):
#     try:
#         user = User(
#             role="PATIENT",
#             name=payload["name"],
#             father_name=payload.get("father_name"),
#             phone=payload["phone"],
#             password_hash=payload["phone"],
#             other_number=payload.get("other_number"),
#             email=payload.get("email"),
#             hospital=HospitalModel.objects.get(id=ObjectId(payload.get("hospital")))
#         ).save()

#         patient = PatientProfile(
#             user=user,
#             age=payload.get("age"),
#             gender=payload.get("gender"),
#             medical_history=payload.get("medical_history"),
#             address=payload.get("address"),
#             service_start=payload.get("service_start"),
#             service_end=payload.get("service_end"),
#             assigned_doctor=payload.get("assigned_doctor"),
#             documents=payload.get("documents", [])   # ✅ HERE
#         ).save()

#         return {"success": True, "patient_id": str(patient.id)}

#     except NotUniqueError:
#         raise HTTPException(status_code=400, detail="Phone already registered")

#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=str(e)
#         )

#     return {"message": "Patient registered", "id": str(patient.id)}


class PatientUpdatePayload(BaseModel):
    # 🔹 USER
    name: Optional[str] = None
    phone: Optional[str] = None
    other_number: Optional[str] = None
    email: Optional[str] = None

    # 🔹 PATIENT
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: Optional[str] = None
    address: Optional[str] = None
    service_start: Optional[str] = None
    service_end: Optional[str] = None

    hospital: Optional[str] = None
    assigned_doctor: Optional[str] = None
    documents: Optional[List[str]] = None
  
    assigned_caretaker : Optional[List[str]] = None
    adharcard : Optional[str] = None
    city : Optional[str] = None
    state : Optional[str] = None
    pincode : Optional[str] = None


@router.put("/{patient_id}/edit")
def update_patient(patient_id: str, payload: PatientUpdatePayload):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    user = patient.user

    # ===== USER UPDATE =====
    if payload.name is not None:
        user.name = payload.name

    if payload.phone is not None:
        exists = User.objects(phone=payload.phone, id__ne=user.id).first()
        if exists:
            raise HTTPException(status_code=400, detail="Phone already exists")
        user.phone = payload.phone

    if payload.other_number is not None:
        user.other_number = payload.other_number

    if payload.email is not None:
        user.email = payload.email

    # 🔥 HOSPITAL UPDATE (FIXED)
    if payload.hospital is not None:
        user.hospital = HospitalModel.objects(id=payload.hospital).first()

    user.save()

    # ===== PATIENT UPDATE =====
    for field in ["age", "gender", "medical_history", "address", "documents"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(patient, field, value)

    if payload.service_start:
        patient.service_start = datetime.strptime(payload.service_start, "%Y-%m-%d")

    if payload.service_end:
        patient.service_end = datetime.strptime(payload.service_end, "%Y-%m-%d")

    if payload.assigned_doctor:
        patient.assigned_doctor = DoctorProfile.objects(
            id=payload.assigned_doctor
        ).first()

    patient.save()

   

    if payload.assigned_caretaker:
       patient.assigned_caretaker = [
        NurseProfile.objects(id=nurse_id).first()
        for nurse_id in payload.assigned_caretaker
    ]

    if payload.adharcard:
        patient.adharcard = payload.adharcard

    if payload.city:
        patient.city = payload.city

    if payload.state:
        patient.state = payload.state

    if payload.pincode:
        patient.pincode = payload.pincode

    patient.save()
    return {
        "success": True,
        "message": "Patient updated successfully"
    }

@router.post("/{patient_id}/add-document")
def add_patient_document(patient_id: str, path: str):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.documents.append(path)
    patient.save()

    return {
        "success": True,
        "documents": patient.documents
    }

@router.put("/{patient_id}/update-document")
def update_patient_document(
    patient_id: str,
    old_path: str,
    new_path: str
):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    if old_path not in patient.documents:
        raise HTTPException(404, "Document not found")

    # 🔁 Replace
    index = patient.documents.index(old_path)
    patient.documents[index] = new_path
    patient.save()

    return {
        "success": True,
        "documents": patient.documents
    }

@router.delete("/{patient_id}/delete-document")
def delete_patient_document(
    patient_id: str,
    path: str
):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    if path not in patient.documents:
        raise HTTPException(404, "Document not found")

    patient.documents.remove(path)
    patient.save()

    return {
        "success": True,
        "documents": patient.documents
    }


@router.post("/me/add-document")
def add_my_document(path: str, user=Depends(get_current_user)):
    patient = PatientProfile.objects(user=user).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    patient.documents.append(path)
    patient.save()

    return {"success": True, "documents": patient.documents}


@router.put("/me/update-document")
def update_my_document(old_path: str, new_path: str, user=Depends(get_current_user)):
    patient = PatientProfile.objects(user=user).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    if old_path not in patient.documents:
        raise HTTPException(404, "Document not found")

    idx = patient.documents.index(old_path)
    patient.documents[idx] = new_path
    patient.save()

    return {"success": True, "documents": patient.documents}


@router.delete("/me/delete-document")
def delete_my_document(path: str, user=Depends(get_current_user)):
    patient = PatientProfile.objects(user=user).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    patient.documents.remove(path)
    patient.save()

    return {"success": True, "documents": patient.documents}


@router.get("/profile/me")
def my_profile(user=Depends(get_current_user)):
    return PatientProfile.objects(user=user).first()

@router.get("/note/list")
def daily_notes(user=Depends(get_current_user)):
    patient = PatientProfile.objects(user=user).first()
    return PatientDailyNote.objects(patient=patient)

@router.get("/vitals/history")
def vitals_history(user=Depends(get_current_user)):
    patient = PatientProfile.objects(user=user).first()
    return PatientVitals.objects(patient=patient)

@router.get("/medication/list")
def medication_list(user=Depends(get_current_user)):
    patient = PatientProfile.objects(user=user).first()
    return PatientMedication.objects(patient=patient)
@router.post("/nurse/patient/note/add")
def add_note(
    patient_id: str,
    note: str,
    user=Depends(get_current_user)
):
    if user.role != "NURSE":
        raise HTTPException(403, "Only nurses allowed")

    from models import NurseProfile
    nurse = NurseProfile.objects(user=user).first()

    return PatientDailyNote(
        patient=patient_id,
        nurse=nurse,
        note=note
    ).save()

@router.post("/nurse/patient/vitals/add")
def add_vitals(
    patient_id: str,
    bp: str,
    pulse: int,
    spo2: int,
    temperature: float,
    sugar: float,
    user=Depends(get_current_user)
):
    if user.role != "NURSE":
        raise HTTPException(403, "Only nurses allowed")

    return PatientVitals(
        patient=patient_id,
        bp=bp,
        pulse=pulse,
        spo2=spo2,
        temperature=temperature,
        sugar=sugar
    ).save()



@router.get("/{patient_id}")
def get_patient(patient_id: str):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    duties = NurseDuty.objects(patient=patient, is_active=True)
    notes = PatientDailyNote.objects(patient=patient).order_by("-created_at")
    vitals = PatientVitals.objects(patient=patient).order_by("-recorded_at")

    return {
        "patient": {
            "id": str(patient.id),
            "name": patient.user.name,
            "phone": patient.user.phone,
            "age": patient.age,
            "gender": patient.gender,
            "medical_history": patient.medical_history
        },
        "duties": duties,
        "notes": notes,
        "vitals": vitals
    }


@router.get("/{patient_id}/care")
def get_patient_care(patient_id: str):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    duties = NurseDuty.objects(patient=patient, is_active=True)
    notes = PatientDailyNote.objects(patient=patient).order_by("-created_at")
    vitals = PatientVitals.objects(patient=patient).order_by("-recorded_at")

    return {
        "patient": {
            "id": str(patient.id),
            "name": patient.user.name,
            "phone": patient.user.phone,
            "othert_number": patient.user.other_number,
            "email": patient.user.email,
            "age": patient.age,
            "gender": patient.gender,
            "medical_history": patient.medical_history,
        },
        "duties": duties,
        "notes": notes,
        "vitals": vitals,
    }

# @router.post("/{patient_id}/assign-nurse")
# def assign_nurse_duty(patient_id: str, payload: dict):
#     patient = PatientProfile.objects(id=patient_id).first()
#     nurse = NurseProfile.objects(id=payload.get("nurse_id")).first()

#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")

#     if not nurse:
#         raise HTTPException(status_code=404, detail="Nurse not found")

#     # 🔥 deactivate previous duties for this patient
#     NurseDuty.objects(
#         patient=patient,
#         is_active=True
#     ).update(set__is_active=False)

#     # ✅ SAFE STRING CAST (VERY IMPORTANT)
#     ward = payload.get("ward")
#     room = payload.get("room")

#     NurseDuty(
#         patient=patient,
#         nurse=nurse,
#         ward=str(ward) if ward is not None else "",
#         room=str(room) if room is not None else "",
#         duty_type=payload.get("duty_type"),
#         shift=payload.get("shift"),
#         duty_start=datetime.fromisoformat(payload.get("duty_start")),
#         duty_end=datetime.fromisoformat(payload.get("duty_end")),
#         is_active=True,
#     ).save()

#     return {
#         "success": True,
#         "message": "Nurse assigned successfully"
#     }


@router.post("/{patient_id}/assign-nurse")
def assign_nurse_duty(patient_id: str, payload: dict):
    patient = PatientProfile.objects(id=patient_id).first()
    nurse = NurseProfile.objects(id=payload.get("nurse_id")).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse not found")

    # 🔥 deactivate previous active duties
    NurseDuty.objects(
        patient=patient,
        is_active=True
    ).update(set__is_active=False)

    duty_location = payload.get("dutyLocation")  # HOME / HOSPITAL
    
    duty = NurseDuty(
        patient=patient,
        nurse=nurse,

        duty_type=payload.get("duty_type"),
        shift=payload.get("shift"),
        dutyLocation=duty_location,

        # 🏥 hospital fields
        ward=payload.get("ward") if duty_location == "HOSPITAL" else None,
        room_no=payload.get("room_no") if duty_location == "HOSPITAL" else None,

        # 🏠 home field
        address=payload.get("address") if duty_location == "HOME" else None,

        duty_start=datetime.fromisoformat(payload.get("duty_start")),
        duty_end=datetime.fromisoformat(payload.get("duty_end")),
        duration_days=payload.get("duration_days", 0),
        price_perday=payload.get("price_perday", 0.0),
        check_in=None,
        check_out=None,
        is_active=True,
    )

    duty.save()

    return {
        "success": True,
        "message": "Nurse assigned successfully"
    }

@router.post("/{patient_id}/daily-note")
def add_daily_note(patient_id: str, payload: dict):
    patient = PatientProfile.objects(id=patient_id).first()
    nurse = NurseProfile.objects(id=payload.get("nurse_id")).first()

    if not patient or not nurse:
        raise HTTPException(status_code=404, detail="Invalid patient or nurse")

    if not payload.get("note"):
        raise HTTPException(status_code=400, detail="Note is required")

    PatientDailyNote(
        patient=patient,
        nurse=nurse,
        note=payload["note"],
    ).save()

    return {"success": True, "message": "Daily note added"}


@router.post("/{patient_id}/vitals")
def add_patient_vitals(patient_id: str, payload: dict):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    PatientVitals(
        patient=patient,
        bp=payload.get("bp"),
        pulse=payload.get("pulse"),
        spo2=payload.get("spo2"),
        temperature=payload.get("temperature"),
        sugar=payload.get("sugar"),
    ).save()

    return {"success": True, "message": "Vitals recorded"}

@router.get("/nurses/list")
def list_nurses():
    nurses = NurseProfile.objects(
        verification_status="APPROVED"
    )
    return [
        {
            "id": str(n.id),
            "name": n.user.name,
            "type": n.nurse_type,
        }
        for n in nurses
    ]


@router.post("/{patient_id}/medication")
def add_medication(patient_id: str, payload: dict):
    """
    payload = {
        "medicine_name": str,
        "dosage": str,
        "timing": ["Morning", "Evening"],  # list of strings
        "duration_days": int
    }
    """
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    med = PatientMedication(
        patient=patient,
        medicine_name=payload.get("medicine_name"),
        dosage=payload.get("dosage"),
        timing=payload.get("timing", []),
        duration_days=payload.get("duration_days"),
        price=payload.get("price", 0.0)
    )
    med.save()
    return {"status": "success", "message": "Medication added successfully"}


# Add a relative access
@router.post("/{patient_id}/relative-access")
def add_relative_access(patient_id: str, payload: dict):
    """
    payload = {
        "relative_user_id": str,
        "access_type": "FREE" or "PAID",
        "permissions": ["VITALS", "NOTES", "BILLING"]
    }
    """
    patient = PatientProfile.objects(id=patient_id).first()
    relative_user = User.objects(id=payload.get("relative_user_id")).first()

    if not patient or not relative_user:
        raise HTTPException(status_code=404, detail="Patient or Relative not found")

    access = RelativeAccess(
        patient=patient,
        relative_user=relative_user,
        access_type=payload.get("access_type", "FREE"),
        permissions=payload.get("permissions", [])
    )
    access.save()
    return {"status": "success", "message": "Relative access added successfully"}


# Remove a relative access
@router.delete("/{patient_id}/relative-access/{access_id}")
def delete_relative_access(patient_id: str, access_id: str):
    access = RelativeAccess.objects(id=access_id, patient=patient_id).first()
    if not access:
        raise HTTPException(status_code=404, detail="Access not found")
    access.delete()
    return {"status": "success", "message": "Relative access removed successfully"}


class PrescribeFromMasterPayload(BaseModel):
    patient_id: str
    medicine_id: str
    timing: list[str]
    duration_days: int
    notes: Optional[List[str]] = []

@router.post("/doctor/prescribe-from-master")
def prescribe_from_master(
    payload: PrescribeFromMasterPayload,
    doctor=Depends(get_current_user)
):
    # 🔹 Validate patient
    patient = PatientProfile.objects(id=payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # 🔹 Validate medicine
    med = Medicine.objects(id=payload.medicine_id, is_active=True).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medicine not found")

    # 🔹 Create prescription
    prescription = PatientMedication(
        patient=patient,
        medicine_name=f"{med.name} ({med.company_name})",
        dosage=med.dosage,
        timing=payload.timing,
        duration_days=payload.duration_days,
        price=med.price,
        notes=payload.notes or []   # ✅ safe default
    )

    prescription.save()

    return {
        "message": "Medicine prescribed successfully",
        "medication_id": str(prescription.id)  # useful for frontend
    }

# @router.post("/doctor/prescribe-from-master")
# def prescribe_from_master(
#     payload: PrescribeFromMasterPayload,
#     doctor=Depends(get_current_user)
# ):
#     patient = PatientProfile.objects(id=payload.patient_id).first()
#     if not patient:
#         raise HTTPException(404, "Patient not found")

#     med = Medicine.objects(id=payload.medicine_id, is_active=True).first()
#     if not med:
#         raise HTTPException(404, "Medicine not found")

#     PatientMedication(
#         patient=patient,
#         medicine_name=f"{med.name} ({med.company_name})",
#         dosage=med.dosage,
#         timing=payload.timing,
#         duration_days=payload.duration_days,
#         price=med.price        # 🔥 AUTO PRICE
#     ).save()

#     return {"message": "Medicine prescribed successfully"}



def user_brief(user):
    if not user:
        return None
    return {
        "id": str(user.id),
        "name": user.name,
        "phone": user.phone,
        "email": user.email,
    }
def serialize_duty(duty):
    return {
        "id": str(duty.id),
        "duty_type": duty.duty_type,
        "shift": duty.shift,
        "start": duty.duty_start,
        "end": duty.duty_end,
        "nurse": {
            "id": str(duty.nurse.id),
            "type": duty.nurse.nurse_type,
            "name": duty.nurse.user.name,
            "phone": duty.nurse.user.phone,
        }
    }



def to_ist(dt):
    if not dt:
        return None

    # 🔥 agar timezone missing hai (naive datetime)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    return dt.astimezone(ZoneInfo("Asia/Kolkata"))

def serialize_note(n):
    return {
        "id": str(n.id),
        "title": getattr(n, "title", None) or "Daily Note",
        "note": n.note,
        "time": to_ist(n.created_at).strftime("%d %b %Y %I:%M %p"),
        "nurse_name": n.nurse.user.name if n.nurse else None,
    }


def serialize_vital(v):
    return {
        "time": v.recorded_at,

        "bp": getattr(v, "bp", None),
        "pulse": getattr(v, "pulse", None),
        "spo2": getattr(v, "spo2", None),
        "temperature": getattr(v, "temperature", None),
        "o2_level": getattr(v, "o2_level", None),
        "rbs": getattr(v, "rbs", None),

        "bipap_ventilator": getattr(v, "bipap_ventilator", None),
        "iv_fluids": getattr(v, "iv_fluids", None),
        "suction": getattr(v, "suction", None),
        "feeding_tube": getattr(v, "feeding_tube", None),

        "vomit_aspirate": getattr(v, "vomit_aspirate", None),
        "urine": getattr(v, "urine", None),
        "stool": getattr(v, "stool", None),

        "other": getattr(v, "other", None),
    }



def serialize_medication(m):
    return {
        "medicine": m.medicine_name,
        "dosage": m.dosage,
        "timing": m.timing,
        "duration": m.duration_days,
        "price": m.price,

        # ✅ ADD THIS
        "notes": getattr(m, "notes", []),
    }

# def serialize_patient(patient):
#     return {
#         "id": str(patient.id),
#         "name": patient.user.name,
#         "phone": patient.user.phone,
#         "age": patient.age,
#         "gender": patient.gender,
#         "address": patient.address,
#         "service_start": patient.service_start,
#         "service_end": patient.service_end,

#         # ✅ NEW
#         "documents": patient.documents or []
#     }

def serialize_patient(patient):
    user = patient.user

    return {
        "id": str(patient.id),

        # USER FIELDS
        "name": user.name,
        "father_name": user.father_name,
        "phone": user.phone,
        "other_number": user.other_number,
        "password_hash":user.password_hash,
        "email": user.email,

        # PATIENT FIELDS
        "age": patient.age,
        "gender": patient.gender,
        "address": patient.address,
        "medical_history": patient.medical_history,
        "service_start": patient.service_start,
        "service_end": patient.service_end,
        "documents": patient.documents or []
    }

@router.get("/profile/view")
def view_patient_profile(user=Depends(get_current_user)):

    # 🔒 Ensure patient only
    if user.role != "PATIENT":
        raise HTTPException(status_code=403, detail="Only patients can view this profile")

    patient = PatientProfile.objects(user=user).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    duties = NurseDuty.objects(
        patient=patient,
        is_active=True
    ).select_related()

    notes = PatientDailyNote.objects(
        patient=patient
    ).order_by("-created_at")

    vitals = PatientVitals.objects(
        patient=patient
    ).order_by("-recorded_at")
    
    medications = PatientMedication.objects(
        patient=patient
    )
    
    return {
        "patient": serialize_patient(patient),
        "duties": [serialize_duty(d) for d in duties],
        "notes": [serialize_note(n) for n in notes],
        "vitals": [serialize_vital(v) for v in vitals],
        "medications": [serialize_medication(m) for m in medications],
    }


@router.get("/{isd}/view")
def view_patient_detailsbjjbj(isd:str):
    patient = PatientProfile.objects(id=isd).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    duties = NurseDuty.objects(patient=patient, is_active=True)
    notes = PatientDailyNote.objects(patient=patient)
    vitals = PatientVitals.objects(patient=patient)
    medications = PatientMedication.objects(patient=patient)

    return {
        "patient": serialize_patient(patient),
        "duties": [serialize_duty(d) for d in duties],
        "notes": [serialize_note(n) for n in notes],
        "vitals": [serialize_vital(v) for v in vitals],
        "medications": [serialize_medication(m) for m in medications],
    }


class PatientProfileUpdate(BaseModel):
    name: str
    father_name: str
    phone: str
    other_number: str
    email: EmailStr
    password_hash : str

    age: int
    gender: str
    address: str
    medical_history: str          # ✅ NEW
    documents: List[str]


@router.put("/profile/update")
def update_patient_profile(
    payload: PatientProfileUpdate,
    user: User = Depends(get_current_user)
):
    if user.role != "PATIENT":
        raise HTTPException(403, "Only patients can update profile")

    patient = PatientProfile.objects(user=user).first()
    if not patient:
        raise HTTPException(404, "Patient profile not found")

    # USER
    user.name = payload.name
    user.father_name = payload.father_name
    user.phone = payload.phone
    user.other_number = payload.other_number
    user.email = payload.email
    user.password_hash = payload.password_hash
    user.save()

    # PATIENT
    patient.age = payload.age
    patient.gender = payload.gender
    patient.address = payload.address
    patient.medical_history = payload.medical_history   # ✅ NEW
    patient.documents = payload.documents
    patient.save()

    return {
        "success": True,
        "message": "Profile updated successfully"
    }


@equipment_router.get("/equipment-getall")
def get_all_equipment():

    equipments = EquipmentTable.objects()

    data = [
        {
            "id": str(e.id),
            "title": e.title,
            "price": e.price,
          
        }
        for e in equipments
    ]

    return data

@equipment_router.post("/create-equipment")
def create_equipment(payload: EquipmentCreate):

    equipment = EquipmentTable(
        title=payload.title,
        image="ddadsa",
        price=payload.price
    ).save()

    return {
        "message": "Equipment created successfully",
        "id": str(equipment.id)
    }


@equipment_router.get("/equipment-get/{equipment_id}")
def get_single_equipment(equipment_id: str):

    equipment = EquipmentTable.objects(id=equipment_id).first()

    if not equipment:
        raise HTTPException(404, "Equipment not found")

    return {
        "id": str(equipment.id),
        "title": equipment.title,
        "image": equipment.image
    }

@equipment_router.put("/equipment-update/{equipment_id}")
def update_equipment(equipment_id: str, payload: EquipmentUpdate):

    equipment = EquipmentTable.objects(id=equipment_id).first()

    if not equipment:
        raise HTTPException(404, "Equipment not found")

    if payload.title is not None:
        equipment.title = payload.title
    
    if payload.price is not None:
        equipment.price = payload.price  

    if payload.image is not None:
        equipment.image = payload.image

    equipment.save()

    return {"message": "Equipment updated successfully"}

@equipment_router.delete("/equipment-delete/{equipment_id}")
def delete_equipment(equipment_id: str):

    equipment = EquipmentTable.objects(id=equipment_id).first()

    if not equipment:
        raise HTTPException(404, "Equipment not found")

    equipment.delete()

    return {"message": "Equipment deleted successfully"}

@equipment_router.post("/request-equipment")
def create_request(payload: EquipmentRequestCreate,user=Depends(get_current_user)):

    patient = PatientProfile.objects(user=user).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    equipment = EquipmentTable.objects(id=payload.equipment_id).first()
    if not equipment:
        raise HTTPException(404, "Equipment not found")

    # prevent duplicate request
    existing = UserEquipmentRequest.objects(
        patient=patient,
        equipment=equipment
    ).first()

    if existing:
        raise HTTPException(400, "Request already exists")

    req = UserEquipmentRequest(
        patient=patient,
        equipment=equipment
    ).save()

    return {
        "message": "Equipment request created",
        "id": str(req.id)
    }

@equipment_router.get("/request-equipment/all")
def get_all_requests():

    requests = UserEquipmentRequest.objects.select_related()

    data = []

    for r in requests:
        data.append({
            "id": str(r.id),
            "patient_id": str(r.patient.id),
            "patient_name": getattr(r.patient.user, "name", ""),
            "patient_phone": getattr(r.patient.user, "phone", ""),
            "ward": str(r.patient.address),
            "equipment_id": str(r.equipment.id),
            "equipment_title": r.equipment.title,
            "equipment_image": r.equipment.image,
            "equipment_price": r.equipment.price,
            "request_time": r.created_at,
    
            "status": r.status
        })
    print(data)

    return data

@equipment_router.get("/request-equipment/patient/{patient_id}")
def get_patient_requests(patient_id: str):

    requests = UserEquipmentRequest.objects(patient=patient_id).select_related()

    data = []

    for r in requests:
        data.append({
            "id": str(r.id),
            "equipment_title": r.equipment.title,
            "equipment_image": r.equipment.image,
            "status": r.status
        })

    return data

@equipment_router.put("/request-equipment/approve/{request_id}")
def update_request(request_id: str, payload: EquipmentRequestUpdate):

    req = UserEquipmentRequest.objects(id=request_id).first()

    if not req:
        raise HTTPException(404, "Request not found")

    if payload.status is not None:
        req.status = payload.status

    req.save()

    return {"message": "Request updated successfully"}

@equipment_router.delete("/request-equipment/delete/{request_id}")
def delete_request(request_id: str):

    req = UserEquipmentRequest.objects(id=request_id).first()

    if not req:
        raise HTTPException(404, "Request not found")

    req.delete()

    return {"message": "Request deleted"}

class EquipmentRow(BaseModel):
    equipment_id: str
    day_duration: int
    price_per_day: float

class AssignEquipmentSchema(BaseModel):
    patient_id: str
    equipments: List[EquipmentRow]


@router.post("/assign-equipment")
async def assign_equipment(data: AssignEquipmentSchema):

    patient = PatientProfile.objects(id=data.patient_id).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    created = []

    for row in data.equipments:

        equipment = EquipmentTable.objects(id=row.equipment_id).first()

        if not equipment:
            continue

        req = UserEquipmentRequest(
            patient=patient,
            equipment=equipment,
            status=True,
            day_duration=row.day_duration,
            price_per_day=row.price_per_day
        )

        req.save()

        created.append(str(req.id))

    return {
        "success": True,
        "assigned": created
    }
