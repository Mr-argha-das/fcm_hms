from fastapi import APIRouter, Depends
from core.dependencies import admin_required
from models import PatientProfile

router = APIRouter(prefix="/admin/patient", tags=["Admin-Patient"])
@router.get("/{patient_id}")
def get_patient(patient_id: str, admin=Depends(admin_required)):
    return PatientProfile.objects(id=patient_id).first()


@router.put("/update")
def update_patient(
    patient_id: str,
    age: int,
    gender: str,
    admin=Depends(admin_required)
):
    patient = PatientProfile.objects(id=patient_id).first()
    patient.age = age
    patient.gender = gender
    patient.save()
    return {"message": "Patient updated"}



