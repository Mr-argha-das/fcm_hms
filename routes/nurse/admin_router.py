from fastapi import APIRouter, Depends, Form, HTTPException, Request
from datetime import date, datetime
from core.dependencies import admin_required, get_current_user
from models import NurseProfile, NurseDuty, NurseSalary, NurseConsent, NurseVisit, PatientProfile
from routes.auth.schemas import NurseVisitCreate

router = APIRouter(prefix="/admin/nurse", tags=["Admin-Nurse"])
@router.post("/approve")
def approve_nurse(nurse_id: str, admin=Depends(admin_required)):
    nurse = NurseProfile.objects(id=nurse_id).first()
    nurse.verification_status = "APPROVED"
    nurse.save()
    return {"message": "Nurse approved"}

@router.post("/reject")
def reject_nurse(nurse_id: str, admin=Depends(admin_required)):
    nurse = NurseProfile.objects(id=nurse_id).first()
    nurse.verification_status = "REJECTED"
    nurse.save()
    return {"message": "Nurse rejected"}
@router.post("/police-status")
def police_status(nurse_id: str, status: str, admin=Depends(admin_required)):
    nurse = NurseProfile.objects(id=nurse_id).first()
    nurse.police_verification_status = status
    nurse.save()

    if status == "FAILED":
        nurse.user.is_active = False
        nurse.user.save()

    return {"message": "Police status updated"}
@router.post("/duty/assign")
def assign_duty(
    nurse_id: str,
    patient_id: str,
    duty_type: str,
    start: datetime,
    end: datetime,
    admin=Depends(admin_required)
):
    nurse = NurseProfile.objects(id=nurse_id).first()

    if NurseDuty.objects(nurse=nurse, is_active=True):
        raise HTTPException(400, "Nurse already on active duty")

    duty = NurseDuty(
        nurse=nurse,
        patient=patient_id,
        duty_type=duty_type,
        duty_start=start,
        duty_end=end
    ).save()

    return {"message": "Duty assigned", "id": str(duty.id)}
@router.post("/duty/change")
def change_duty(
    duty_id: str,
    start: datetime,
    end: datetime,
    admin=Depends(admin_required)
):
    duty = NurseDuty.objects(id=duty_id).first()
    duty.duty_start = start
    duty.duty_end = end
    duty.save()
    return {"message": "Duty updated"}
@router.post("/salary/generate")
def generate_salary(
    nurse_id: str,
    month: str,
    amount: float,
    admin=Depends(admin_required)
):
    nurse = NurseProfile.objects(id=nurse_id).first()

    salary = NurseSalary(
        nurse=nurse,
        month=month,
        basic_salary=amount,
        deductions=0,
        net_salary=amount
    ).save()

    return {"message": "Salary generated"}
@router.post("/salary/mark-paid")
def mark_paid(salary_id: str, admin=Depends(admin_required)):
    salary = NurseSalary.objects(id=salary_id).first()
    salary.is_paid = True
    salary.save()
    return {"message": "Salary marked paid"}
@router.post("/consent/revoke")
def revoke_consent(nurse_id: str, admin=Depends(admin_required)):
    consent = NurseConsent.objects(nurse=nurse_id, status="SIGNED").first()
    if consent:
        consent.status = "REVOKED"
        consent.save()

    NurseDuty.objects(nurse=nurse_id, is_active=True).update(is_active=False)
    return {"message": "Consent revoked & duty blocked"}

@router.post("/admin/visit")
def admin_create_visit(
    payload: NurseVisitCreate,
    nurse_id: str,
    visit_time: datetime,
    admin= Depends(admin_required)
):
   # Admin can create visits for any nurse
    if not nurse:
       raise HTTPException(status_code=404, detail="Nurse not found")
    if not patient:
       raise HTTPException(status_code=404, detail="Patient not found")
   

    nurse = NurseProfile.objects(id=nurse_id).first()
    patient = PatientProfile.objects(id=payload.patient_id).first()

    visit = NurseVisit(
        nurse=nurse,
        patient=patient,
        duty=payload.duty_id,
        ward=payload.ward,
        room_no=payload.room_no,
        visit_type=payload.visit_type,
        notes=payload.notes,
        visit_time=visit_time,
        created_by=admin
    )
    visit.save()

    return {"message": "Visit created by admin"}
@router.post("/{nurse_id}/update")
async def update_nurse_admin(
    nurse_id: str,
    request: Request,

    # ---- VERIFICATION ----
    aadhaar_verified: bool = Form(False),
    police_verification_status: str = Form(...),

    # ---- PROFILE ----
    nurse_type: str = Form(...),
    joining_date: date | None = Form(None),
    resignation_date: date | None = Form(None),
    is_active: bool = Form(False),

    # ---- SALARY ----
    salary_type: str = Form(...),
    salary_amount: float = Form(...),
    payment_mode: str = Form(...),
    salary_date: int = Form(...)
):
    print("🔥 UPDATE API HIT:", nurse_id)
    print("📦 FORM DATA:", await request.form())

    nurse = NurseProfile.objects(id=nurse_id).first()
    if not nurse:
        raise HTTPException(404, "Nurse not found")

    # ================= UPDATE NURSE =================
    nurse.aadhaar_verified = aadhaar_verified
    nurse.police_verification_status = police_verification_status
    nurse.nurse_type = nurse_type
    nurse.joining_date = joining_date
    nurse.resignation_date = resignation_date
    nurse.save()

    # ================= UPDATE USER =================
    if nurse.user:
        nurse.user.is_active = is_active
        nurse.user.save()

    # ================= CONSENT =================
    consent = NurseConsent.objects(nurse=nurse, status="PENDING").first()

    if not consent:
        consent = NurseConsent(
            nurse=nurse,
            shift_type="DAY",
            duty_hours=8
        )

    consent.salary_type = salary_type
    consent.salary_amount = salary_amount
    consent.payment_mode = payment_mode
    consent.salary_date = salary_date
    consent.save()

    print("✅ UPDATED SUCCESSFULLY")

    return {"success": True}