from fastapi import APIRouter, Depends, Form, HTTPException
from datetime import datetime

from fastapi.responses import RedirectResponse
from core.dependencies import get_current_user
from models import (
    DoctorProfile, DoctorVisit,
    PatientProfile, PatientVitals, PatientMedication
)

router = APIRouter(prefix="/doctor", tags=["Doctor"])
@router.post("/profile/create")
def create_profile(
    specialization: str,
    registration_number: str,
    experience_years: int,
    user=Depends(get_current_user)
):
    if user.role != "DOCTOR":
        raise HTTPException(403, "Only doctors allowed")

    if DoctorProfile.objects(user=user).first():
        raise HTTPException(400, "Profile already exists")

    doc = DoctorProfile(
        user=user,
        specialization=specialization,
        registration_number=registration_number,
        experience_years=experience_years,
        available=False  # admin approval needed
    ).save()

    return {"message": "Doctor profile created", "id": str(doc.id)}
@router.get("/profile/me")
def my_profile(user=Depends(get_current_user)):
    return DoctorProfile.objects(user=user).first()
@router.post("/availability")
def toggle_availability(
    available: bool,
    user=Depends(get_current_user)
):
    doctor = DoctorProfile.objects(user=user).first()
    if not doctor:
        raise HTTPException(404, "Doctor profile not found")

    doctor.available = available
    doctor.save()

    return {"message": f"Availability set to {available}"}
@router.get("/patients")
def my_patients(user=Depends(get_current_user)):
    doctor = DoctorProfile.objects(user=user).first()
    return PatientProfile.objects(assigned_doctor=doctor)
@router.post("/visit/start")
def start_visit(
    patient_id: str,
    visit_type: str,
    user=Depends(get_current_user)
):
    doctor = DoctorProfile.objects(user=user).first()

    patient = PatientProfile.objects(id=patient_id).first()
    if patient.assigned_doctor != doctor:
        raise HTTPException(403, "Patient not assigned to you")

    visit = DoctorVisit(
        doctor=doctor,
        patient=patient,
        visit_type=visit_type,
        visit_time=datetime.utcnow()
    ).save()

    return {"message": "Visit started", "visit_id": str(visit.id)}
@router.post("/visit/complete")
def complete_visit(
    visit_id: str,
    assessment_notes: str,
    treatment_plan: str,
    user=Depends(get_current_user)
):
    doctor = DoctorProfile.objects(user=user).first()
    visit = DoctorVisit.objects(id=visit_id).first()

    if visit.doctor != doctor:
        raise HTTPException(403, "Unauthorized visit access")

    visit.assessment_notes = assessment_notes
    visit.treatment_plan = treatment_plan
    visit.save()

    return {"message": "Visit completed"}
@router.get("/visit/history/{patient_id}")
def visit_history(patient_id: str, user=Depends(get_current_user)):
    doctor = DoctorProfile.objects(user=user).first()
    return DoctorVisit.objects(
        doctor=doctor,
        patient=patient_id
    )
@router.get("/patient/vitals/{patient_id}")
def patient_vitals(patient_id: str, user=Depends(get_current_user)):
    doctor = DoctorProfile.objects(user=user).first()
    patient = PatientProfile.objects(id=patient_id).first()

    if patient.assigned_doctor != doctor:
        raise HTTPException(403, "Access denied")

    return PatientVitals.objects(patient=patient)
@router.post("/patient/medication/add")
def add_medication(
    patient_id: str,
    medicine_name: str,
    dosage: str,
    timing: list[str],
    duration_days: int,
    user=Depends(get_current_user)
):
    doctor = DoctorProfile.objects(user=user).first()
    patient = PatientProfile.objects(id=patient_id).first()

    if patient.assigned_doctor != doctor:
        raise HTTPException(403, "Patient not assigned")

    med = PatientMedication(
        patient=patient,
        medicine_name=medicine_name,
        dosage=dosage,
        timing=timing,
        duration_days=duration_days
    ).save()

    return {"message": "Medication added", "id": str(med.id)}

