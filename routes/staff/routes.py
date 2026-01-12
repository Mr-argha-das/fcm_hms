from fastapi  import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from core.dependencies import get_current_user
from models import *
from datetime import datetime
from mongoengine.errors import NotUniqueError
router = APIRouter(prefix="/staff", tags=["Attendance"])


@router.get(
    "/staff/{user_id}/attendance-salary",
    response_class=HTMLResponse
)
def attendance_salary(
    user_id: str,
    request: Request,
    month: str | None = None
):
    if not month:
        month = datetime.utcnow().strftime("%Y-%m")

    user = User.objects(id=user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    # ===============================
    # NURSE
    # ===============================
    if user.role == "NURSE":
        nurse = NurseProfile.objects(user=user).first()

        attendance = NurseAttendance.objects(
            nurse=nurse,
            date__startswith=month
        )

        salary = NurseSalary.objects(
            nurse=nurse,
            month=month
        ).first()

        template = "admin/nurse_attendance_salary.html"

        context = {
            "staff": nurse,
            "role": "NURSE",
            "attendance": attendance,
            "salary": salary,
            "month": month
        }

    # ===============================
    # DOCTOR
    # ===============================
    elif user.role == "DOCTOR":
        doctor = DoctorProfile.objects(user=user).first()

        attendance = DoctorAttendance.objects(
            doctor=doctor,
            date__startswith=month
        )

        salary = DoctorSalary.objects(
            doctor=doctor,
            month=month
        ).first()

        template = "admin/doctor_attendance_salary.html"

        context = {
            "staff": doctor,
            "role": "DOCTOR",
            "attendance": attendance,
            "salary": salary,
            "month": month
        }

    # ===============================
    # OTHER STAFF
    # ===============================
    else:
        staff = StaffProfile.objects(user=user).first()

        attendance = StaffAttendance.objects(
            staff=staff,
            date__startswith=month
        )

        salary = StaffSalary.objects(
            staff=staff,
            month=month
        ).first()

        template = "admin/staff_attendance_salary.html"

        context = {
            "staff": staff,
            "role": "STAFF",
            "attendance": attendance,
            "salary": salary,
            "month": month
        }

    context["request"] = request
    return templates.TemplateResponse(template, context)


