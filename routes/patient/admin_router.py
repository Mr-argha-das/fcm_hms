from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from core.dependencies import admin_required
from models import PatientProfile

router = APIRouter(prefix="/admin/patient", tags=["Admin-Patient"])


def _get_patient_or_404(patient_id: str) -> PatientProfile:
    """Return the patient or a clean 404 (never a 500 on bad ids)."""
    try:
        oid = ObjectId(patient_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Patient not found")
    patient = PatientProfile.objects(id=oid).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/{patient_id}")
def get_patient(patient_id: str, admin=Depends(admin_required)):
    return _get_patient_or_404(patient_id)


@router.put("/update")
def update_patient(
    patient_id: str,
    age: int,
    gender: str,
    admin=Depends(admin_required)
):
    patient = _get_patient_or_404(patient_id)
    patient.age = age
    patient.gender = gender
    patient.save()
    return {"message": "Patient updated"}
