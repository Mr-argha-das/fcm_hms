from fastapi import APIRouter, Depends
from core.dependencies import get_current_user
from models import Complaint

router = APIRouter(prefix="/complaint", tags=["Complaint"])
@router.post("/create")
def create_complaint(message: str, user=Depends(get_current_user)):
    comp = Complaint(
        raised_by=user,
        message=message,
        status="OPEN"
    ).save()
    return {"message": "Complaint submitted"}
@router.get("/my")
def my_complaints(user=Depends(get_current_user)):
    return Complaint.objects(raised_by=user)
