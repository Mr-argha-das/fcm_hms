from fastapi import APIRouter, Depends, HTTPException
from core.dependencies import get_current_user
from models import (
    Medicine, NurseDuty, NurseProfile, PatientProfile, PatientDailyNote,
    PatientVitals, PatientMedication, RelativeAccess, User
)
from datetime import datetime
from mongoengine.errors import NotUniqueError
router = APIRouter(prefix="/patient", tags=["Patient"])

@router.post("/create")
def create_patient(payload: dict):
    try:
        # 🔹 CREATE USER
        user = User(
            role="PATIENT",
            name=payload["name"],
            phone=payload["phone"],
            other_number=payload.get("other_number"),
            email=payload.get("email"),
        ).save()

        # 🔹 CREATE PATIENT PROFILE
        patient = PatientProfile(
            user=user,
            age=payload.get("age"),
            gender=payload.get("gender"),
            medical_history=payload.get("medical_history"),
            address=payload.get("address"),              # ✅ NEW
            service_start=payload.get("service_start"),
            service_end=payload.get("service_end"),
            assigned_doctor=payload.get("assigned_doctor") or None,
        ).save()

        return {
            "success": True,
            "patient_id": str(patient.id)
        }

    except NotUniqueError:
        raise HTTPException(
            status_code=400,
            detail="Phone number already registered"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return {"message": "Patient registered", "id": str(patient.id)}
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
# @router.post("/{patient_id}/assign-nurse")
# def assign_nurse(patient_id: str, payload: dict):
#     patient = PatientProfile.objects(id=patient_id).first()
#     nurse = NurseProfile.objects(id=payload["nurse_id"]).first()

#     if not patient or not nurse:
#         raise HTTPException(404, "Invalid patient or nurse")

#     NurseDuty(
#         nurse=nurse,
#         patient=patient,
#         duty_type=payload["duty_type"],
#         shift=payload["shift"],
#         duty_start=datetime.fromisoformat(payload["duty_start"]),
#         duty_end=datetime.fromisoformat(payload["duty_end"])
#     ).save()

#     return {"success": True}

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

    if not patient or not nurse:
        raise HTTPException(status_code=404, detail="Invalid patient or nurse")

    # 🔥 deactivate previous duties
    NurseDuty.objects(patient=patient, is_active=True).update(
        set__is_active=False
    )

    NurseDuty(
        patient=patient,
        nurse=nurse,
        duty_type=payload.get("duty_type"),
        shift=payload.get("shift"),
        duty_start=datetime.fromisoformat(payload.get("duty_start")),
        duty_end=datetime.fromisoformat(payload.get("duty_end")),
        is_active=True,
    ).save()

    return {"success": True, "message": "Nurse assigned successfully"}
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

@router.post("/doctor/prescribe-from-master")
def prescribe_from_master(
    patient_id: str,
    medicine_id: str,
    timing: list[str],
    duration_days: int,
    doctor=Depends(get_current_user)
):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    med = Medicine.objects(id=medicine_id, is_active=True).first()
    if not med:
        raise HTTPException(404, "Medicine not found")

    PatientMedication(
        patient=patient,
        medicine_name=f"{med.name} ({med.company_name})",
        dosage=med.dosage,
        timing=timing,
        duration_days=duration_days,
        price=med.price        # 🔥 AUTO PRICE
    ).save()

    return {"message": "Medicine prescribed successfully"}