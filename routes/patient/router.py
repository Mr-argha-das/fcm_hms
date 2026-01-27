import json
from typing import Optional , List
from urllib import request

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from core.dependencies import get_current_user
from models import (
    Medicine, NurseDuty, NurseProfile, PatientProfile, PatientDailyNote,
    PatientVitals, PatientMedication, RelativeAccess, User
)
from datetime import datetime
from mongoengine.errors import NotUniqueError
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/patient", tags=["Patient"])

@router.post("/create")
def create_patient(payload: dict):
    try:
        user = User(
            role="PATIENT",
            name=payload["name"],
            father_name=payload.get("father_name"),
            phone=payload["phone"],
            other_number=payload.get("other_number"),
            email=payload.get("email"),
        ).save()

        patient = PatientProfile(
            user=user,
            age=payload.get("age"),
            gender=payload.get("gender"),
            medical_history=payload.get("medical_history"),
            address=payload.get("address"),
            service_start=payload.get("service_start"),
            service_end=payload.get("service_end"),
            assigned_doctor=payload.get("assigned_doctor"),
            documents=payload.get("documents", [])   # ✅ HERE
        ).save()

        return {"success": True, "patient_id": str(patient.id)}

    except NotUniqueError:
        raise HTTPException(status_code=400, detail="Phone already registered")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return {"message": "Patient registered", "id": str(patient.id)}

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

@router.post("/{patient_id}/assign-nurse")
def assign_nurse_duty(patient_id: str, payload: dict):
    patient = PatientProfile.objects(id=patient_id).first()
    nurse = NurseProfile.objects(id=payload.get("nurse_id")).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse not found")

    # 🔥 deactivate previous duties for this patient
    NurseDuty.objects(
        patient=patient,
        is_active=True
    ).update(set__is_active=False)

    # ✅ SAFE STRING CAST (VERY IMPORTANT)
    ward = payload.get("ward")
    room = payload.get("room")

    NurseDuty(
        patient=patient,
        nurse=nurse,
        ward=str(ward) if ward is not None else "",
        room=str(room) if room is not None else "",
        duty_type=payload.get("duty_type"),
        shift=payload.get("shift"),
        duty_start=datetime.fromisoformat(payload.get("duty_start")),
        duty_end=datetime.fromisoformat(payload.get("duty_end")),
        is_active=True,
    ).save()

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
def serialize_note(n):
    return {
        "id": str(n.id),
        "note": n.note,
        "time": n.created_at,
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


# def serialize_medication(m):
#     return {
#         "medicine": m.medicine_name,
#         "dosage": m.dosage,
#         "timing": m.timing,
#         "duration": m.duration_days,
#         "price": m.price,
#     }

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
