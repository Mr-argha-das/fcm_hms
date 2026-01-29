import calendar
from collections import defaultdict
from datetime import date, timedelta
from http.client import HTTPException
import json
from core.dependencies import get_current_user , role_required
from fastapi import APIRouter, Request , Depends
from fastapi.params import Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from models import *

router = APIRouter(prefix="/admin", tags=["Admin Pages"])

templates = Jinja2Templates(directory="templates")




@router.get("/user-list")
def admin_home(request: Request):
    return json.loads(User.objects.all().to_json())

# -------------------------
# AUTH
# -------------------------
# @router.get("/login", response_class=HTMLResponse)
# def admin_login(request: Request):
#     return templates.TemplateResponse(
#         "admin/login.html", {"request": request}
#     )
@router.get("/login", response_class=HTMLResponse)
def admin_login(request: Request):
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request}
    )
# @router.get("/login", response_class=HTMLResponse)
# def admin_login(request: Request):

#     try:
#         user = get_current_user(request)
#         if user:
#             return RedirectResponse("/admin/dashboard")
#     except:
#         pass

#     return templates.TemplateResponse(
#         "admin/login.html",
#         {"request": request}
#     )

# =====================================================
@router.get("/about", response_class=HTMLResponse)
def about_page(request: Request):

    about = AboutUs.objects.first()

    return templates.TemplateResponse(
        "admin/about_us.html",
        {
            "request": request,
            "about": about
        }
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


# @router.get("/dashboard", response_class=HTMLResponse)
# def dashboard(request: Request):
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user = Depends(get_current_user)):

    if user.role == "NURSE":
        return RedirectResponse("/admin/nurses")

    if user.role == "DOCTOR":
        return RedirectResponse("/admin/doctors")

    if user.role == "PATIENT":
        return RedirectResponse("/admin/patients")
    
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
    # sos_alerts = SOSAlert.objects.order_by("-created_at").limit(5)
    # ======================
# SOS ALERTS
# ======================
    raw_sos = SOSAlert.objects.order_by("-created_at").limit(5)

    sos_alerts = []

    for alert in raw_sos:
     sos_alerts.append({
        "triggered_by": alert.triggered_by.name if alert.triggered_by else "-",
        "patient_name": alert.patient.user.name if alert.patient and alert.patient.user else "-",
        "message": alert.message,
        "location": alert.location["coordinates"] if alert.location else None,
        "status": alert.status,
        "created_at": alert.created_at.strftime("%d %b %H:%M")
    })
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



@router.get("/nurse-dashboard", response_class=HTMLResponse)
def nurse_dashboard(
    request: Request,
    user = Depends(role_required(["NURSE"]))
):
    # basic data (abhi empty, next step me bharenge)
    return templates.TemplateResponse(
        "admin/nurse_dashboard.html",
        {
            "request": request
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


@router.get("/create/patient", response_class=HTMLResponse)
def create_patient_page(request: Request):

    doctors = DoctorProfile.objects(available=True)

    return templates.TemplateResponse(
        "admin/add_pataint.html",
        {
            "request": request,
            "doctors": doctors
        }
    )
# -------------------------
# NURSE MODULE
# -------------------------
# @router.get("/nurses", response_class=HTMLResponse)
# def nurses(request: Request):

#     nurses_qs = NurseProfile.objects(created_by="ADMIN").select_related()

#     return templates.TemplateResponse(
#         "admin/nurses.html",
#         {
#             "request": request,
#             "nurses": nurses_qs
#         }
#     )

@router.get("/nurses", response_class=HTMLResponse)
def nurses(
    request: Request,
    user = Depends(role_required(["ADMIN", "NURSE"]))
):
    nurses_qs = NurseProfile.objects(created_by="ADMIN").select_related()

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
# @router.get("/doctors", response_class=HTMLResponse)
# def doctors(request: Request):

#     doctors_qs = DoctorProfile.objects.select_related()

#     return templates.TemplateResponse(
#         "admin/doctors.html",
#         {
#             "request": request,
#             "doctors": doctors_qs
#         }
#     )

@router.get("/doctors", response_class=HTMLResponse)
def doctors(
    request: Request,
    user = Depends(role_required(["ADMIN", "DOCTOR"]))
):
    doctors_qs = DoctorProfile.objects()  # select_related bhi hata hua hai (safe)

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
# @router.get("/patients", response_class=HTMLResponse)
# def patients(request: Request):

#     patients_qs = PatientProfile.objects.select_related()

#     return templates.TemplateResponse(
#         "admin/patients.html",
#         {
#             "request": request,
#             "patients": patients_qs
#         }
#     )
@router.get("/patients", response_class=HTMLResponse)
def patients(
    request: Request,
    user = Depends(role_required(["ADMIN", "NURSE", "DOCTOR", "PATIENT"]))
):

    patients_qs = PatientProfile.objects.select_related()

    return templates.TemplateResponse(
        "admin/patients.html",
        {
            "request": request,
            "patients": patients_qs
        }
    )



# @router.get("/nurse/visit-page/{nurse_id}", response_class=HTMLResponse)
# def nurse_visit_page(request: Request, nurse_id: str):

#     patients = PatientProfile.objects.select_related()

#     return templates.TemplateResponse(
#         "admin/nurse_visit_create.html",
#         {
#             "request": request,
#             "patients": patients
#         }
#     )


@router.get("/visit-page", response_class=HTMLResponse)
def visit_page(request: Request):

    patients = PatientProfile.objects.select_related()
    nurses = NurseProfile.objects.select_related()

    return templates.TemplateResponse(
        "admin/nurse_visit_create.html",
        {
            "request": request,
            "patients": patients,
            "nurses": nurses
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
    print("SOS Alerts Count:", sos_qs.to_json())
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
    print("Other Number:", user.other_number)
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
    print("Profile Photo:",  nurse.profile_photo)

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
def edit_nurse(nurse_id: str, request: Request):
    nurse = NurseProfile.objects(id=nurse_id).first()
    if not nurse:
        raise HTTPException(404, "Nurse not found")

    patients = PatientProfile.objects()
    duties = NurseDuty.objects(nurse=nurse, is_active=True).order_by("-duty_start")
    visits = NurseVisit.objects(nurse=nurse).order_by("-visit_time")[:10]
    consent = NurseConsent.objects(nurse=nurse).order_by("-created_at").first()

    return templates.TemplateResponse(
        "admin/nurse_edit.html",
        {
            "request": request,
            "nurse": nurse,
            "patients": patients,
            "duties": duties,
            "visits": visits,
            "consent": consent
        }
    )
@router.get("/create/doctor", response_class=HTMLResponse)
def doctor_create_page(request: Request):
    return templates.TemplateResponse(
        "admin/doctor_create.html",
        {"request": request}
    )


    return user
@router.get("/doctors/{doctor_id}", response_class=HTMLResponse)
def doctor_detail_page(doctor_id: str, request: Request):

    doctor = DoctorProfile.objects(id=doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")

    user = doctor.user

    # 🔹 Assigned Patients (ONLY 20)
    patients = PatientProfile.objects(
        assigned_doctor=doctor
    ).order_by("-service_start")[:20]

    # 🔹 Total Patients Count
    total_patients = PatientProfile.objects(
        assigned_doctor=doctor
    ).count()

    return templates.TemplateResponse(
        "admin/doctor_detail.html",
        {
            "request": request,
            "doctor": doctor,
            "user": user,

            # 👇 doctor visits ki jagah
            "patients": patients,

            # 👇 stats ke liye
            "total_patients": total_patients,
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


@router.get("/patient/{patient_id}/care", response_class=HTMLResponse)
def render_patient_care(
    request: Request,
    patient_id: str
):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    nurses = NurseProfile.objects()
    duties = NurseDuty.objects(patient=patient, is_active=True)
    notes = PatientDailyNote.objects(patient=patient).order_by("-created_at")
    vitals = PatientVitals.objects(patient=patient).order_by("-recorded_at")

    return templates.TemplateResponse(
        "admin/edit_patient.html",
        {
            "request": request,
            "patient": patient,
            "doctor": patient.assigned_doctor,
            "nurses": nurses,
            "duties": duties,
            "notes": notes,
            "vitals": vitals,
        }
    )


@router.get("/patient/{patient_id}/view", response_class=HTMLResponse)
def view_patient_details(request: Request, patient_id: str):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    nurses = NurseProfile.objects()
    duties = NurseDuty.objects(patient=patient, is_active=True)
    notes = PatientDailyNote.objects(patient=patient).order_by("-created_at")
    vitals = PatientVitals.objects(patient=patient).order_by("-recorded_at")
    medications = PatientMedication.objects(patient=patient)
    relatives = RelativeAccess.objects(patient=patient)
    relatives = RelativeAccess.objects(patient=patient)
    all_users = User.objects(role="RELATIVE")
    
    return templates.TemplateResponse(
        "admin/view_patient.html",
        {
            "request": request,
            "patient": patient,
            "doctor": patient.assigned_doctor,
            "nurses": nurses,
            "duties": duties,
            "notes": notes,
            "vitals": vitals,
            "medications": medications,
            "relatives": relatives,
            "relatives": relatives,
        }
    )




@router.get("/staff/{user_id}/attendance-salary", response_class=HTMLResponse)
def attendance_salary(request: Request, user_id: str, month: str | None = None):
    from bson import ObjectId
    from datetime import datetime

    if not month or month.strip() == "":
        month = datetime.utcnow().strftime("%Y-%m")

    # Convert string id to ObjectId
    try:
        user = User.objects(id=ObjectId(user_id)).first()
    except:
        raise HTTPException(404, "Invalid User ID")

    if not user:
        raise HTTPException(404, "User not found")

    context = {"request": request, "month": month, "user": user}

    if user.role == "NURSE":
        staff = NurseProfile.objects(user=user).first()
        attendance = NurseAttendance.objects(nurse=staff, date__startswith=month)
        salary = NurseSalary.objects(nurse=staff, month=month).first()
        template = "admin/nurse_attendance_salary.html"

    elif user.role == "DOCTOR":
        staff = DoctorProfile.objects(user=user).first()
        attendance = DoctorAttendance.objects(doctor=staff, date__startswith=month)
        salary = DoctorSalary.objects(doctor=staff, month=month).first()
        template = "admin/doctor_attendance_salary.html"

    else:
        staff = StaffProfile.objects(user=user).first()
        attendance = StaffAttendance.objects(staff=staff, date__startswith=month)
        salary = StaffSalary.objects(staff=staff, month=month).first()
        template = "admin/staff_attendance_salary.html"

    context.update({"staff": staff, "attendance": attendance, "salary": salary, "role": user.role})

    # Chart
    chart_labels = [a.date.strftime("%d") for a in attendance] if attendance else []
    chart_values = [1 if a.check_in else 0 for a in attendance] if attendance else []
    context.update({"chart_labels": chart_labels, "chart_values": chart_values})

    return templates.TemplateResponse(template, context)


@router.post("/staff/{user_id}/mark-paid")
def mark_salary_paid(user_id: str, month: str = Form(...)):
    user = User.objects(id=user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    if user.role == "NURSE":
        staff = NurseProfile.objects(user=user).first()
        salary = NurseSalary.objects(nurse=staff, month=month).first()
        if salary:
            salary.is_paid = True
            salary.save()
    elif user.role == "DOCTOR":
        staff = DoctorProfile.objects(user=user).first()
        salary = DoctorSalary.objects(doctor=staff, month=month).first()
        if salary:
            salary.is_paid = True
            salary.save()
    else:
        staff = StaffProfile.objects(user=user).first()
        salary = StaffSalary.objects(staff=staff, month=month).first()
        if salary:
            salary.is_paid = True
            salary.save()

    return RedirectResponse(f"/admin/staff/{user_id}/attendance-salary?month={month}", status_code=303)

@router.get("/sos/{sos_id}", response_class=HTMLResponse)
def sos_details_page(
    request: Request,
    sos_id: str,
):
    sos = SOSAlert.objects(id=sos_id).first()
    if not sos:
        raise HTTPException(404, "SOS not found")

    patient = sos.patient

    doctor = patient.assigned_doctor if patient else None

    duty = None
    nurse_profile = None
    nurse_user = None

    if patient:
        duty = NurseDuty.objects(
            patient=patient,
            is_active=True
        ).first()

        if duty:
            nurse_profile = duty.nurse
            nurse_user = nurse_profile.user if nurse_profile else None

    return templates.TemplateResponse(
        "admin/sos_details.html",
        {
            "request": request,
            "sos": sos,
            "patient": patient,
            "doctor": doctor,
            "duty": duty,
            "nurse": nurse_profile,
            "nurse_user": nurse_user,
        }
    )



@router.get("/medicine", response_class=HTMLResponse)
def medicine_master_page(
    request: Request,
   
):
    return templates.TemplateResponse(
        "admin/medicine/index.html",
        {"request": request}
    )



@router.get("/staff/manage", response_class=HTMLResponse)
def staff_manage_page(request: Request):
    staff = User.objects(role="STAFF").order_by("-created_at")
    return templates.TemplateResponse(
        "admin/staff_manage.html",
        {
            "request": request,
            "staff": staff
        }
    )
