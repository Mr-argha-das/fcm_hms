from fastapi import APIRouter, Depends, HTTPException
from core.dependencies import get_current_user
from models import (
    RelativeAccess, PatientVitals,
    PatientDailyNote, PatientInvoice
)

router = APIRouter(prefix="/relative", tags=["Relative"])
@router.post("/request-access")
def request_access(patient_id: str, user=Depends(get_current_user)):
    if user.role != "RELATIVE":
        raise HTTPException(403, "Only relatives allowed")

    if RelativeAccess.objects(relative_user=user).count() >= 1:
        raise HTTPException(400, "Free relative already used")

    access = RelativeAccess(
        patient=patient_id,
        relative_user=user,
        access_type="FREE",
        permissions=["VITALS"]
    ).save()

    return {"message": "Access requested", "id": str(access.id)}
@router.post("/upgrade-paid")
def upgrade_paid(access_id: str, user=Depends(get_current_user)):
    access = RelativeAccess.objects(id=access_id, relative_user=user).first()
    access.access_type = "PAID"
    access.permissions = ["VITALS", "NOTES", "BILLING"]
    access.save()
    return {"message": "Upgraded to paid access"}
@router.get("/patient-data")
def patient_data(patient_id: str, user=Depends(get_current_user)):
    access = RelativeAccess.objects(
        patient=patient_id,
        relative_user=user
    ).first()

    if not access:
        raise HTTPException(403, "No access")

    data = {
        "vitals": PatientVitals.objects(patient=patient_id)
    }

    if access.access_type == "PAID":
        data["notes"] = PatientDailyNote.objects(patient=patient_id)
        data["billing"] = PatientInvoice.objects(patient=patient_id)

    return data
