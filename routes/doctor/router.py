


from fastapi import APIRouter, Depends, Form, HTTPException, status
from datetime import datetime

from fastapi.responses import RedirectResponse
from core.dependencies import get_current_user
from models import (
    DoctorProfile, DoctorVisit,
    PatientProfile, PatientVitals, PatientMedication, User
)

router = APIRouter(prefix="/doctor", tags=["Doctor"])

@router.post("/profile/create")
def create_profile(
    specialization: str,
    registration_number: str,
    experience_years: int,
    user=Depends(get_current_user)
):
    if user.role != "DOCTOR":
        raise HTTPException(403, "Only doctors allowed")

    if DoctorProfile.objects(user=user).first():
        raise HTTPException(400, "Profile already exists")

    doc = DoctorProfile(
        user=user,
        specialization=specialization,
        registration_number=registration_number,
        experience_years=experience_years,
        available=False  # admin approval needed
    ).save()

    return {"message": "Doctor profile created", "id": str(doc.id)}

@router.put("/profile/update")
async def update_profile(
    data: dict,
    user=Depends(get_current_user)
):
    profile = DoctorProfile.objects(user=user).first()

    if not profile:
        raise HTTPException(404, "Profile not found")

    # =========================
    # UPDATE USER NAME
    # =========================
    if "name" in data:
        user.name = data["name"]
        user.save()

    # =========================
    # UPDATE PROFILE FIELDS
    # =========================
    if "specialization" in data:
        profile.specialization = data["specialization"]

    if "experience_years" in data:
        profile.experience_years = data["experience_years"]

    profile.save()

    return {"message": "Profile updated successfully"}

@router.get("/profile/me")
def my_profile(user=Depends(get_current_user)):
    profile = DoctorProfile.objects(user=user).first()

    if not profile:
        raise HTTPException(404, "Profile not found")

    return {
        "name": user.name,   # 🔥 added
        "phone": user.phone,  # 🔥 added
        "specialization": profile.specialization,
        "experience_years": profile.experience_years,
        "available": profile.available
    }

@router.post("/availability")
def toggle_availability(
    available: bool,
    user=Depends(get_current_user)
):
    doctor = DoctorProfile.objects(user=user).first()
    if not doctor:
        raise HTTPException(404, "Doctor profile not found")

    doctor.available = available
    doctor.save()

    return {"message": f"Availability set to {available}"}

@router.get("/patients")
def my_patients(user=Depends(get_current_user)):
    doctor = DoctorProfile.objects(user=user).first()
    if not doctor:
        raise HTTPException(404, "Doctor profile not found")

    patients = PatientProfile.objects(
        assigned_doctor=doctor
    ).limit(20)

    return {
        "total": PatientProfile.objects(
            assigned_doctor=doctor
        ).count(),
        "patients": [
            {
                "id": str(p.id),
                "name": p.user.name,
                "phone": p.user.phone,
                "age": p.age,
                "gender": p.gender,
                "address": p.address,
                "service_start": p.service_start,
                "service_end": p.service_end,
            }
            for p in patients
        ]
    }
@router.post("/visit/start")
def start_visit(
    patient_id: str,
    visit_type: str,
    user=Depends(get_current_user)
):
    doctor = DoctorProfile.objects(user=user).first()

    patient = PatientProfile.objects(id=patient_id).first()
    if patient.assigned_doctor != doctor:
        raise HTTPException(403, "Patient not assigned to you")

    visit = DoctorVisit(
        doctor=doctor,
        patient=patient,
        visit_type=visit_type,
        visit_time=datetime.utcnow()
    ).save()

    return {"message": "Visit started", "visit_id": str(visit.id)}

@router.post("/visit/complete")
def complete_visit(
    visit_id: str,
    assessment_notes: str,
    treatment_plan: str,
    user=Depends(get_current_user)
):
    doctor = DoctorProfile.objects(user=user).first()
    visit = DoctorVisit.objects(id=visit_id).first()

    if visit.doctor != doctor:
        raise HTTPException(403, "Unauthorized visit access")

    visit.assessment_notes = assessment_notes
    visit.treatment_plan = treatment_plan
    visit.save()

    return {"message": "Visit completed"}

@router.get("/visit/history/{patient_id}")
def visit_history(patient_id: str, user=Depends(get_current_user)):
    doctor = DoctorProfile.objects(user=user).first()
    return DoctorVisit.objects(
        doctor=doctor,
        patient=patient_id
    )
@router.get("/patient/vitals/{patient_id}")
def patient_vitals(patient_id: str, user=Depends(get_current_user)):
    doctor = DoctorProfile.objects(user=user).first()
    patient = PatientProfile.objects(id=patient_id).first()

    if patient.assigned_doctor != doctor:
        raise HTTPException(403, "Access denied")

    return PatientVitals.objects(patient=patient)
@router.post("/patient/medication/add")
def add_medication(
    patient_id: str,
    medicine_name: str,
    dosage: str,
    timing: list[str],
    duration_days: int,
    user=Depends(get_current_user)
):
    doctor = DoctorProfile.objects(user=user).first()
    patient = PatientProfile.objects(id=patient_id).first()

    if patient.assigned_doctor != doctor:
        raise HTTPException(403, "Patient not assigned")

    med = PatientMedication(
        patient=patient,
        medicine_name=medicine_name,
        dosage=dosage,
        timing=timing,
        duration_days=duration_days
    ).save()

    return {"message": "Medication added", "id": str(med.id)}

@router.post("/doctor/prescribe-medicine")
def prescribe_medicine(
    patient_id: str,
    medicine_name: str,
    dosage: str,
    timing: list[str],
    duration_days: int,
    doctor=Depends(get_current_user)
):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    med = PatientMedication(
        patient=patient,
        medicine_name=medicine_name,
        dosage=dosage,
        timing=timing,
        duration_days=duration_days
    )
    med.save()

    return {"message": "Medicine prescribed"}


def doctor_required(user: User = Depends(get_current_user)):
    if user.role != "DOCTOR":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Doctor access required"
        )
    
@router.get(
    "/my-patients",
    dependencies=[Depends(doctor_required)],
)
def my_patients_api(
    current_user: User = Depends(get_current_user),
):
    # 🔹 Doctor profile from token user
    doctor = DoctorProfile.objects(user=current_user).first()
    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    # 🔹 Only assigned patients (limit 20)
    patients_qs = PatientProfile.objects(
        assigned_doctor=doctor
    ).limit(20)

    patients = []
    for patient in patients_qs:
        user = patient.user
        patients.append({
            "patient_id": str(patient.id),
            "name": user.name,
            "phone": user.phone,
            "age": patient.age,
            "gender": patient.gender,
            "address": patient.address,
            "service_start": patient.service_start,
            "service_end": patient.service_end,
        })

    total_patients = PatientProfile.objects(
        assigned_doctor=doctor
    ).count()

    return {
        "doctor": {
            "id": str(doctor.id),
            "name": current_user.name,
            "phone": current_user.phone,
            "specialization": doctor.specialization,
            "experience_years": doctor.experience_years,
        },
        "total_patients": total_patients,
        "patients": patients,
    }