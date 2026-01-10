import calendar
from collections import defaultdict
from datetime import date, timedelta
from http.client import HTTPException
import json
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from models import *

router = APIRouter(prefix="/admin", tags=["Admin Pages"])

templates = Jinja2Templates(directory="templates")


@router.get("/user-list")
def admin_home(request: Request):
    return json.loads(User.objects.all().to_json())

# -------------------------
# AUTH
# -------------------------
@router.get("/login", response_class=HTMLResponse)
def admin_login(request: Request):
    return templates.TemplateResponse(
        "admin/login.html", {"request": request}
    )


@router.get("/nurses/self", response_class=HTMLResponse)
def self_registered_nurses(request: Request):

    nurses_qs = (
        NurseProfile.objects(created_by="SELF")
        .select_related()
       
    )

    return templates.TemplateResponse(
        "admin/nurses_self.html",
        {
            "request": request,
            "nurses": nurses_qs
        }
    )
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):

    now = datetime.now()

    # ======================
    # KPI
    # ======================
    total_patients = PatientProfile.objects.count()

    active_nurses = NurseProfile.objects(
        verification_status="APPROVED"
    ).count()

    total_doctors = DoctorProfile.objects.count()

    # ======================
    # MONTHLY REVENUE
    # ======================
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    invoices = PatientInvoice.objects(
        created_at__gte=start_month,
        status="PAID"
    )

    monthly_revenue = sum(inv.total_amount for inv in invoices)

    # ======================
    # RECENT ACTIVITY
    # ======================
    recent_activity = []

    for note in PatientDailyNote.objects.order_by("-created_at").limit(3):
        recent_activity.append("Daily note added")

    for visit in DoctorVisit.objects.order_by("-created_at").limit(2):
        recent_activity.append("Doctor visit completed")

    # ======================
    # SOS ALERTS
    # ======================
    sos_alerts = SOSAlert.objects.order_by("-created_at").limit(5)

    # ======================
    # TODAY DATE RANGE (IMPORTANT FIX)
    # ======================
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # ======================
    # TODAY SCHEDULE (FIXED)
    # ======================
    today_schedule = []

    nurse_duties = NurseDuty.objects(
        duty_start__gte=today_start,
        duty_start__lt=today_end
    )

    for duty in nurse_duties:
        today_schedule.append(
            f"Nurse duty ({duty.shift}) at {duty.duty_start.strftime('%H:%M')}"
        )

    doctor_visits = DoctorVisit.objects(
        visit_time__gte=today_start,
        visit_time__lt=today_end
    )

    for visit in doctor_visits:
        today_schedule.append(
            f"Doctor visit at {visit.visit_time.strftime('%H:%M')}"
        )

    # ======================
    # PATIENT CHART (LAST 7 DAYS) – FIXED
    # ======================
    chart_labels = []
    chart_values = []

    for i in range(6, -1, -1):
        day_start = today_start - timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        count = PatientProfile.objects(
            service_start__gte=day_start.date(),
            service_start__lt=day_end.date()
        ).count()

        chart_labels.append(day_start.strftime("%d %b"))
        chart_values.append(count)

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,

            # KPI
            "total_patients": total_patients,
            "active_nurses": active_nurses,
            "total_doctors": total_doctors,
            "monthly_revenue": round(monthly_revenue, 2),

            # Lists
            "recent_activity": recent_activity,
            "sos_alerts": sos_alerts,
            "today_schedule": today_schedule,

            # Chart
            "chart_labels": chart_labels,
            "chart_values": chart_values
        }
    )
# -------------------------
# USERS
# -------------------------
@router.get("/users", response_class=HTMLResponse)
def users(request: Request):
    return templates.TemplateResponse(
        "admin/users.html", {"request": request}
    )
@router.get("/create/nurse", response_class=HTMLResponse)
def create_nurse(request: Request):
    return templates.TemplateResponse(
        "admin/nurse_create.html", {"request": request}
    )

# -------------------------
# NURSE MODULE
# -------------------------
@router.get("/nurses", response_class=HTMLResponse)
def nurses(request: Request):

    nurses_qs = NurseProfile.objects.select_related()

    return templates.TemplateResponse(
        "admin/nurses.html",
        {
            "request": request,
            "nurses": nurses_qs
        }
    )
@router.get("/duty/assign", response_class=HTMLResponse)
def duty_assign(request: Request):
    return templates.TemplateResponse(
        "admin/duty_assign.html", {"request": request}
    )


@router.get("/duty/manage", response_class=HTMLResponse)
def duty_manage(request: Request):
    return templates.TemplateResponse(
        "admin/duty_manage.html", {"request": request}
    )


@router.get("/duty/live", response_class=HTMLResponse)
def duty_live(request: Request):
    return templates.TemplateResponse(
        "admin/duty_live.html", {"request": request}
    )


@router.get("/attendance", response_class=HTMLResponse)
def attendance(request: Request):
    return templates.TemplateResponse(
        "admin/attendance.html", {"request": request}
    )


@router.get("/salary", response_class=HTMLResponse)
def salary(request: Request):
    return templates.TemplateResponse(
        "admin/salary.html", {"request": request}
    )


@router.get("/consent", response_class=HTMLResponse)
def consent(request: Request):
    return templates.TemplateResponse(
        "admin/consent.html", {"request": request}
    )


# -------------------------
# DOCTOR MODULE
# -------------------------
@router.get("/doctors", response_class=HTMLResponse)
def doctors(request: Request):

    doctors_qs = DoctorProfile.objects.select_related()

    return templates.TemplateResponse(
        "admin/doctors.html",
        {
            "request": request,
            "doctors": doctors_qs
        }
    )
@router.get("/doctor/assign", response_class=HTMLResponse)
def doctor_assign(request: Request):
    return templates.TemplateResponse(
        "admin/doctor_assign.html", {"request": request}
    )


@router.get("/doctor/visits", response_class=HTMLResponse)
def doctor_visits(request: Request):
    return templates.TemplateResponse(
        "admin/doctor_visits.html", {"request": request}
    )


# -------------------------
# PATIENT MODULE
# -------------------------
@router.get("/patients", response_class=HTMLResponse)
def patients(request: Request):

    patients_qs = PatientProfile.objects.select_related()

    return templates.TemplateResponse(
        "admin/patients.html",
        {
            "request": request,
            "patients": patients_qs
        }
    )

@router.get("/patient/vitals", response_class=HTMLResponse)
def patient_vitals(request: Request):
    return templates.TemplateResponse(
        "admin/patient_vitals.html", {"request": request}
    )


@router.get("/patient/notes", response_class=HTMLResponse)
def patient_notes(request: Request):
    return templates.TemplateResponse(
        "admin/patient_notes.html", {"request": request}
    )


# -------------------------
# RELATIVE MODULE
# -------------------------
@router.get("/relatives", response_class=HTMLResponse)
def relatives(request: Request):
    return templates.TemplateResponse(
        "admin/relatives.html", {"request": request}
    )


# -------------------------
# BILLING
# -------------------------
@router.get("/billing", response_class=HTMLResponse)
def billing(request: Request):

    invoices_qs = PatientInvoice.objects.order_by("-created_at")

    return templates.TemplateResponse(
        "admin/billing.html",
        {
            "request": request,
            "invoices": invoices_qs
        }
    )

# -------------------------
# SOS & COMPLAINTS
# -------------------------
@router.get("/sos", response_class=HTMLResponse)
def sos(request: Request):

    sos_qs = (
        SOSAlert.objects
        .order_by("-created_at")
        
    )

    return templates.TemplateResponse(
        "admin/sos.html",
        {
            "request": request,
            "sos_alerts": sos_qs,
            "now": datetime.utcnow()
        }
    )

@router.get("/complaints", response_class=HTMLResponse)
def complaints(request: Request):

    complaints_qs = (
        Complaint.objects
        .order_by("-id")   # latest first (created_at nahi hai model me)
        
    )

    return templates.TemplateResponse(
        "admin/complaints.html",
        {
            "request": request,
            "complaints": complaints_qs
        }
    )

# -------------------------
# NOTIFICATIONS
# -------------------------
@router.get("/notifications", response_class=HTMLResponse)
def notifications(request: Request):

    notifications_qs = (
        Notification.objects
        .order_by("-created_at")
        
    )

    return templates.TemplateResponse(
        "admin/notifications.html",
        {
            "request": request,
            "notifications": notifications_qs
        }
    )


@router.get("/nurses/{nurse_id}")
def nurse_detail_page(
    nurse_id: str,
    request: Request,
    month: str = datetime.utcnow().strftime("%Y-%m")  # YYYY-MM
):
    print("\n========== NURSE DETAIL PAGE ==========")
    print("Nurse ID:", nurse_id)
    print("Month:", month)

    nurse = NurseProfile.objects(id=nurse_id).first()
    if not nurse:
        raise HTTPException(404, "Nurse not found")

    user = nurse.user

    # ================= MONTH RANGE =================
    year, mon = map(int, month.split("-"))
    last_day = calendar.monthrange(year, mon)[1]

    start_date = date(year, mon, 1)
    end_date = date(year, mon, last_day)

    print("Date Range:", start_date, "to", end_date)

    # ================= ATTENDANCE =================
    attendance_qs = NurseAttendance.objects(
        nurse=nurse,
        date__gte=start_date,
        date__lte=end_date
    ).order_by("date")

    total_present = attendance_qs.count()

    print("Total Attendance:", total_present)

    # -------- GRAPH DATA (Day-wise count) --------
    attendance_map = defaultdict(int)
    for att in attendance_qs:
        attendance_map[att.date.day] += 1

    chart_labels = list(range(1, last_day + 1))
    chart_values = [attendance_map.get(day, 0) for day in chart_labels]

    print("Attendance Chart Labels:", chart_labels)
    print("Attendance Chart Values:", chart_values)

    # ================= SALARY =================
    salary = NurseSalary.objects(
        nurse=nurse,
        month=month
    ).first()

    print("Salary:", salary.net_salary if salary else "N/A")

    # ================= DUTY =================
    active_duty = NurseDuty.objects(
        nurse=nurse,
        is_active=True
    ).first()

    print("Active Duty:", active_duty.duty_type if active_duty else "None")

    # ================= VISITS =================
    visits = NurseVisit.objects(
        nurse=nurse
    ).order_by("-visit_time")[:10]

    print("Recent Visits:", visits.count())

    # ================= CONSENT =================
    consent = NurseConsent.objects(
        nurse=nurse
    ).order_by("-created_at").first()

    print("Consent Status:", consent.status if consent else "None")

    # ================= COMPLETE NURSE DUMP =================
    print("\n--- USER DATA ---")
    print("Phone:", user.phone)
    print("Email:", user.email)
    print("Role:", user.role)

    print("\n--- NURSE PROFILE ---")
    print("Type:", nurse.nurse_type)
    print("Aadhaar:", nurse.aadhaar_number)
    print("Verified:", nurse.verification_status)
    print("Police Verification:", nurse.police_verification_status)
    print("Joining:", nurse.joining_date)
    print("Resignation:", nurse.resignation_date)
    print("Qualification Docs:", nurse.qualification_docs)
    print("Experience Docs:", nurse.experience_docs)
    print("Profile Photo:", nurse.profile_photo)

    print("========================================\n")

    return templates.TemplateResponse(
        "admin/nurse_detail.html",
        {
            "request": request,

            # BASIC
            "nurse": nurse,
            "user": user,
            "month": month,

            # ATTENDANCE
            "attendance": attendance_qs,
            "total_present": total_present,

            # GRAPH
            "chart_labels": chart_labels,
            "chart_values": chart_values,

            # OTHERS
            "salary": salary,
            "duty": active_duty,
            "visits": visits,
            "consent": consent
        }
    )


@router.get("/nurses/{nurse_id}/edit", response_class=HTMLResponse)
def nurse_edit_page(nurse_id: str, request: Request):
    nurse = NurseProfile.objects(id=nurse_id).first()
    if not nurse:
        raise HTTPException(404, "Nurse not found")

    consent = NurseConsent.objects(nurse=nurse).order_by("-created_at").first()

    return templates.TemplateResponse(
        "admin/nurse_edit.html",
        {
            "request": request,
            "nurse": nurse,
            "consent": consent
        }
    )
@router.get("/create/doctor", response_class=HTMLResponse)
def doctor_create_page(request: Request):
    return templates.TemplateResponse(
        "admin/doctor_create.html",
        {"request": request}
    )

@router.get("/doctors/{doctor_id}", response_class=HTMLResponse)
def doctor_detail_page(doctor_id: str, request: Request):
    doctor = DoctorProfile.objects(id=doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")

    user = doctor.user

    # 🔹 Visits
    visits = DoctorVisit.objects(
        doctor=doctor
    ).order_by("-visit_time")[:10]

    total_visits = DoctorVisit.objects(doctor=doctor).count()

    # 🔹 Assigned patients (unique)
    patient_ids = DoctorVisit.objects(
        doctor=doctor
    ).distinct("patient")

    total_patients = len(patient_ids)

    return templates.TemplateResponse(
        "admin/doctor_detail.html",
        {
            "request": request,
            "doctor": doctor,
            "user": user,
            "visits": visits,
            "total_visits": total_visits,
            "total_patients": total_patients
        }
    )

@router.get("/doctors/{doctor_id}/edit", response_class=HTMLResponse)
def doctor_edit_page(doctor_id: str, request: Request):
    doctor = DoctorProfile.objects(id=doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")

    return templates.TemplateResponse(
        "admin/doctor_edit.html",
        {
            "request": request,
            "doctor": doctor,
            "user": doctor.user
        }
    )