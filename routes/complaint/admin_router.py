from fastapi import APIRouter, Depends
from core.dependencies import admin_required
from models import Complaint

router = APIRouter(prefix="/admin/complaint", tags=["Admin-Complaint"])
@router.get("/all")
def all_complaints(admin=Depends(admin_required)):
    return Complaint.objects()
@router.post("/resolve")
def resolve_complaint(complaint_id: str, admin=Depends(admin_required)):
    comp = Complaint.objects(id=complaint_id).first()
    comp.status = "RESOLVED"
    comp.save()
    return {"message": "Complaint resolved"}
