from fastapi import APIRouter, Depends, HTTPException
from core.dependencies import get_current_user
from models import (
    PatientProfile, PatientDailyNote,
    PatientVitals, PatientMedication
)

router = APIRouter(prefix="/patient", tags=["Patient"])
@router.post("/profile/create")
def create_profile(
    age: int,
    gender: str,
    medical_history: str = "",
    user=Depends(get_current_user)
):
    if user.role != "PATIENT":
        raise HTTPException(403, "Only patients allowed")

    if PatientProfile.objects(user=user).first():
        raise HTTPException(400, "Profile already exists")

    patient = PatientProfile(
        user=user,
        age=age,
        gender=gender,
        medical_history=medical_history
    ).save()

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
