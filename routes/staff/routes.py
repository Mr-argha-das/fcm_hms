from dataclasses import Field
from typing import Optional
from fastapi  import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from core.dependencies import admin_required, get_current_user
from models import *
from datetime import datetime
from mongoengine.errors import NotUniqueError
from pydantic  import BaseModel
router = APIRouter(prefix="/staff", tags=["Attendance"])


class StaffCreateBody(BaseModel):
    name: Optional[str] = None
    father_name: Optional[str] = None
    phone: str
    other_number: Optional[str] = None
    email: Optional[str] = None

class StaffUpdateBody(BaseModel):
    name: str | None = None
    father_name: str | None = None
    email: str | None = None
    other_number: str | None = None




@router.get("/profile")
def get_my_staff_profile(user=Depends(get_current_user)):
    if user.role != "STAFF":
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": str(user.id),
        "role": user.role,
        "name": user.name,
        "father_name": user.father_name,
        "phone": user.phone,
        "other_number": user.other_number,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }
@router.put("/profile")
def update_my_staff_profile(
    body: StaffUpdateBody,
    user=Depends(admin_required)
):
    if user.role != "STAFF":
        raise HTTPException(status_code=403, detail="Access denied")

    if body.name is not None:
        user.name = body.name
    if body.father_name is not None:
        user.father_name = body.father_name
    if body.email is not None:
        user.email = body.email
    if body.other_number is not None:
        user.other_number = body.other_number

    user.save()

    return {"message": "Profile updated successfully"}

@router.post("/create")
def create_staff(
    body: StaffCreateBody,
    admin=Depends(get_current_user)
):
    # 🔐 Only ADMIN can create staff
    if admin.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin can create staff")

    try:
        user = User(
            role="STAFF",
            name=body.name,
            father_name=body.father_name,
            phone=body.phone,
            other_number=body.other_number,
            email=body.email,
            otp_verified=False,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        user.save()

    except NotUniqueError:
        raise HTTPException(
            status_code=400,
            detail="Phone number already exists"
        )

    return {
        "message": "Staff created successfully",
        "staff": {
            "id": str(user.id),
            "name": user.name,
            "phone": user.phone,
            "role": user.role,
        }
    }
@router.get("/list")
def get_all_staff(
    include_inactive: bool = False,
    admin=Depends(get_current_user)
):
    if admin.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    query = {
        "role": "STAFF"
    }

    if not include_inactive:
        query["is_active"] = True

    staff_list = User.objects(**query).order_by("-created_at")

    return {
        "total": staff_list.count(),
        "staff": [
            {
                "id": str(s.id),
                "name": s.name,
                "phone": s.phone,
                "email": s.email,
                "father_name": s.father_name,
                "other_number": s.other_number,
                "is_active": s.is_active,
                "created_at": s.created_at
            }
            for s in staff_list
        ]
    }