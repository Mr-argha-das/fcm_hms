from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.params import Form
from fastapi.responses import HTMLResponse, RedirectResponse
from core.dependencies import admin_required
from models import DoctorProfile, DoctorVisit, PatientProfile, User

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


@router.post("/create-new")
def create_doctor(
    name :  str | None = Form(None), 
    phone: str = Form(...),
    email: str | None = Form(None),
    specialization: str | None = Form(None),
    registration_number: str | None = Form(None),
    experience_years: int | None = Form(None),
    available: bool = Form(True)
):
    print("AVAILABLE:", name )

    # 🔍 Check existing user
    if User.objects(phone=phone).first():
        raise HTTPException(400, "Phone already registered")

    # 👤 Create User
    user = User(
        role="DOCTOR",
        name=name,
        phone=phone,
        email=email,
        is_active=True,
        created_at=datetime.utcnow()
    ).save()

    # 🧑‍⚕️ Create Doctor Profile
    doctor = DoctorProfile(
        user=user,
        specialization=specialization,
        registration_number=registration_number,
        experience_years=experience_years,
        available=available
    ).save()

    return {
        "success": True,
        "doctor_id": str(doctor.id)
    }

@router.post("/doctors/{doctor_id}/update")
def update_doctor(
    doctor_id: str,
    specialization: str = Form(...),
    registration_number: str = Form(...),
    experience_years: int = Form(...),
    available: bool = Form(...)
):
    doctor = DoctorProfile.objects(id=doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")

    doctor.update(
        set__specialization=specialization,
        set__registration_number=registration_number,
        set__experience_years=experience_years,
        set__available=available
    )

    return RedirectResponse(
        url=f"/admin/doctors/{doctor_id}",
        status_code=302
    )
