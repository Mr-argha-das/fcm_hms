from datetime import timedelta
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