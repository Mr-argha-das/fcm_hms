from fastapi import APIRouter, Depends
from core.dependencies import admin_required
from models import DoctorProfile, PatientProfile

router = APIRouter(prefix="/admin/doctor", tags=["Admin-Doctor"])

@router.post("/approve")
def approve_doctor(doctor_id: str, admin=Depends(admin_required)):
    doctor = DoctorProfile.objects(id=doctor_id).first()
    doctor.available = True
    doctor.save()
    return {"message": "Doctor approved & activated"}
@router.post("/assign-patient")
def assign_patient(
    doctor_id: str,
    patient_id: str,
    admin=Depends(admin_required)
):
    doctor = DoctorProfile.objects(id=doctor_id).first()
    patient = PatientProfile.objects(id=patient_id).first()

    patient.assigned_doctor = doctor
    patient.save()

    return {"message": "Patient assigned to doctor"}
