import admin
from fastapi import APIRouter, Depends
from core.dependencies import admin_required, get_current_user
from models import Complaint, User
from pydantic import BaseModel
router = APIRouter(prefix="/admin/complaint", tags=["Admin-Complaint"])

def complaint_serializer(complaint: Complaint):
    return {
        "id": str(complaint.id),
        "raised_by": {
            "id": str(complaint.raised_by.id),
            "name": complaint.raised_by.name,
            "phone": complaint.raised_by.phone,
            "role": complaint.raised_by.role
        },
        "message":  f"Raised by {complaint.raised_by.name} : { complaint.message}",
        "status": complaint.status
    }
@router.get("/all")
def all_complaints():
    return [complaint_serializer(c) for c in Complaint.objects().order_by("-created_at")]
@router.post("/resolve")
def resolve_complaint(complaint_id: str):
    comp = Complaint.objects(id=complaint_id).first()
    comp.status = "RESOLVED"
    comp.save()
    return {"message": "Complaint resolved"}

@router.post("/in-progress")
def mark_complaint_in_progress(complaint_id: str):
    comp = Complaint.objects(id=complaint_id).first()
    if comp.status == "RESOLVED":
        return {"message": "Complaint already resolved"}
    if comp.status == "IN_PROGRESS":
        return {"message": "Complaint already in-progress"}
    comp.status = "IN_PROGRESS"
    comp.save()
    return {"message": "Complaint marked as in-progress"}


class ComplaintBody(BaseModel):
    message : str
@router.post("/create")
def create_complaint(message: ComplaintBody, admin=Depends(get_current_user)):
    comp = Complaint(raised_by=admin, message=message.message)
    comp.save()
    return {"message": "Complaint created", "id": str(comp.id)}
@router.get("/my-complaints")
def my_complaints(user=Depends(get_current_user)):
    comps = Complaint.objects(raised_by=user)
    return [complaint_serializer(c) for c in comps]