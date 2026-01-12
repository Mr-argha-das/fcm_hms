import json
from fastapi import APIRouter, Depends
from datetime import datetime
from core.dependencies import admin_required, get_current_user
from models import DoctorProfile, SOSAlert, PatientProfile, Notification, NurseDuty
from pydantic import BaseModel
router = APIRouter(prefix="/sos", tags=["SOS"])

class SOSRequest(BaseModel):
    message: str
@router.post("/trigger")
def trigger_sos(patient_id: str, message:SOSRequest, user=Depends(get_current_user)):
    sos = SOSAlert(
        triggered_by=user,
        patient=patient_id,
        message=message.message,
        created_at=datetime.utcnow()
    ).save()

    # Notify Admin
    Notification(
        user=None,
        title="SOS ALERT",
        message=f"SOS triggered for patient {patient_id}"
    ).save()

    # Notify Assigned Nurse
    duty = NurseDuty.objects(patient=patient_id, is_active=True).first()
    if duty:
        Notification(
            user=duty.nurse.user,
            title="SOS ALERT",
            message="Emergency for your patient"
        ).save()

    return {"message": "SOS triggered"}
@router.get("/admin/active")
def active_sos(admin=Depends(admin_required)):
    return SOSAlert.objects()
@router.post("/admin/resolve-admin")
def resolve_sos(sos_id: str, admin=Depends(admin_required)):
    sos = SOSAlert.objects(id=sos_id).first()
    sos.status = "RESOLVED"
    sos.save()
    return {"message": "SOS resolved"}

@router.post("/admin/resolve-doctor")
def resolve_sos(sos_id: str, admin=Depends(get_current_user)):
    sos = SOSAlert.objects(id=sos_id).first()
    sos.status = "RESOLVED"
    sos.save()
    return {"message": "SOS resolved"}

@router.get("/doctor/active")
def active_sos(user=Depends(get_current_user)):
    doctor = DoctorProfile.objects(user=user).first()
    sos = SOSAlert.objects(patient__assigned_doctor=doctor)
    return {
        "active_sos": json.loads(sos.to_json())
    }