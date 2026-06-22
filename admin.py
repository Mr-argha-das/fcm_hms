import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta
import os
import uuid
import json
from typing import List, Optional
from core.dependencies import admin_required, get_current_user , role_required
from core.permissions import ADMIN_MODULES, get_admin_menu
from core.site_settings import get_site_settings
from fastapi import APIRouter, Request , Depends, HTTPException, Query, UploadFile, File
from fastapi.params import Form
from pydantic import BaseModel

from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from models import *
from mongoengine.errors import NotUniqueError
from mongoengine.queryset.visitor import Q
router = APIRouter(prefix="/admin", tags=["Admin Pages"])

templates = Jinja2Templates(directory="templates")
templates.env.globals["get_admin_menu"] = get_admin_menu
templates.env.globals["get_site_settings"] = get_site_settings


def save_settings_upload(file: UploadFile | None, current_path: str | None) -> str | None:
    if not file or not file.filename:
        return current_path

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "png"
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        raise HTTPException(400, "Only JPG, PNG or WEBP image files are allowed")

    upload_dir = os.path.join("media", "settings")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as out_file:
        out_file.write(file.file.read())

    return f"/media/settings/{filename}"


def ensure_patient_profiles_for_registered_users():
    for patient_user in User.objects(role="PATIENT"):
        if not PatientProfile.objects(user=patient_user).first():
            PatientProfile(user=patient_user, created_by="SELF").save()


def admin_patient_filter(hospital_id: str | None = None):
    patient_users = User.objects(
        role="PATIENT",
        name__exists=True,
        name__nin=["", None],
    ).only("id")

    if hospital_id:
        patient_users = patient_users.filter(hospital=hospital_id)

    return Q(created_by__ne="SELF") & Q(user__in=patient_users)




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
@router.get("/lead/create", response_class=HTMLResponse)
def admin_login(request: Request):
    return templates.TemplateResponse(
        "admin/lead_create.html",
        {"request": request}
    )
@router.get("/login", response_class=HTMLResponse)
def admin_login(request: Request):
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request}
    )


@router.get("/settings", response_class=HTMLResponse)
def site_settings_page(request: Request, admin=Depends(admin_required)):
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "settings": get_site_settings(),
        }
    )


@router.post("/settings", response_class=HTMLResponse)
def update_site_settings(
    request: Request,
    company_name: str = Form(""),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    gst_number: str = Form(""),
    bank_name: str = Form(""),
    account_number: str = Form(""),
    ifsc_code: str = Form(""),
    pin_code: str = Form(""),
    account_holder_name: str = Form(""),
    upi_id: str = Form(""),
    logo_file: UploadFile | None = File(None),
    qr_file: UploadFile | None = File(None),
    admin=Depends(admin_required),
):
    settings = get_site_settings()

    settings.company_name = company_name.strip() or "We Care Home Healthcare"
    settings.address = address.strip()
    settings.phone = phone.strip()
    settings.email = email.strip() or None
    settings.gst_number = gst_number.strip()
    settings.bank_name = bank_name.strip()
    settings.account_number = account_number.strip()
    settings.ifsc_code = ifsc_code.strip()
    settings.pin_code = pin_code.strip()
    settings.account_holder_name = account_holder_name.strip()
    settings.upi_id = upi_id.strip()
    settings.logo_path = save_settings_upload(logo_file, settings.logo_path)
    settings.qr_path = save_settings_upload(qr_file, settings.qr_path)
    settings.updated_at = datetime.utcnow()
    settings.save()

    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "settings": settings,
            "success": "Settings updated successfully",
        }
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
        .filter(nurse_type__ne="CARETAKER")
        .select_related()
       
    )
    return templates.TemplateResponse(
        "admin/nurses_self.html",
        {
            "request": request,
            "nurses": nurses_qs,
            "page_title": "Self Registered Nurses",
            "page_description": "Nurses who signed up themselves (Admin approval pending)",
            "active_tab": "nurses",
            "empty_message": "No self registered nurses found",
            "detail_base": "/admin/nurses",
            "edit_base": "/admin/nurses",
        }
    )


@router.get("/nurses/self/caretacker", response_class=HTMLResponse)
def self_registered_caretakers(request: Request):
    caretakers_qs = (
        NurseProfile.objects(created_by="SELF", nurse_type="CARETAKER")
        .select_related()
    )

    return templates.TemplateResponse(
        "admin/nurses_self.html",
        {
            "request": request,
            "nurses": caretakers_qs,
            "page_title": "Self Registered Caretakers",
            "page_description": "Caretakers who signed up themselves (Admin approval pending)",
            "active_tab": "caretakers",
            "empty_message": "No self registered caretakers found",
            "detail_base": "/admin/caretacker",
            "edit_base": "/admin/caretacker",
        }
    )


# @router.get("/dashboard", response_class=HTMLResponse)
# def dashboard(request: Request):

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    start: str | None = None,
    end: str | None = None,
    hospital_id: str | None = None,
    user = Depends(get_current_user)
):
    # ======================
    # ROLE REDIRECTS
    # ======================
    if user.role == "NURSE":
        return RedirectResponse("/admin/nurses")
    if user.role == "DOCTOR":
        return RedirectResponse("/admin/doctors")
    if user.role == "PATIENT":
        return RedirectResponse("/admin/patients")

    now = datetime.now()
    ensure_patient_profiles_for_registered_users()

    # ======================
    # DATE RANGE
    # ======================
    if start and end:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
    else:
        start_date = now.replace(day=1, hour=0, minute=0, second=0)
        end_date = now + timedelta(days=1)

    # ======================
    # HOSPITAL → USERS
    # ======================
    user_filter = {}

    if hospital_id:
        hospital_users = User.objects(
            hospital=hospital_id
        ).only("id")

        user_filter["user__in"] = hospital_users

    # ======================
    # DROPDOWN DATA
    # ======================
    hospitals = HospitalModel.objects.only("id", "name", "branch")

    # ======================
    # KPI
    # ======================
    patient_filter = admin_patient_filter(hospital_id)

    total_patients = PatientProfile.objects(
        patient_filter
    ).count()

    discharged_patients = PatientProfile.objects(
        patient_filter,
        service_end__exists=True,
        service_end__ne=None
    ).count()

    total_nurses = NurseProfile.objects(
        **user_filter
    ).count()

    total_doctors = DoctorProfile.objects(
        **user_filter
    ).count()

    # ======================
    # REVENUE (SAFE VERSION)
    # ======================
    invoices = PatientInvoice.objects(
        created_at__gte=start_date,
        created_at__lt=end_date,
        status="PAID"
    ).only("total_amount")

    monthly_revenue = sum(i.total_amount or 0 for i in invoices)

    # ======================
    # RECENT ACTIVITY
    # ======================
    recent_activity = []

    for note in PatientDailyNote.objects.order_by("-created_at").limit(3).select_related():
        if not hospital_id or note.patient.user in hospital_users:
            recent_activity.append(
                f"Note added for {note.patient.user.name}"
            )

    for visit in DoctorVisit.objects.order_by("-created_at").limit(2).select_related():
        if not hospital_id or visit.patient.user in hospital_users:
            recent_activity.append(
                f"Doctor visit for {visit.patient.user.name}"
            )

    # ======================
    # SOS ALERTS
    # ======================
    sos_alerts = []

    for alert in SOSAlert.objects.order_by("-created_at").limit(5).select_related():
        if hospital_id and alert.patient and alert.patient.user not in hospital_users:
            continue

        sos_alerts.append({
            "triggered_by": alert.triggered_by.name if alert.triggered_by else "-",
            "patient_name": alert.patient.user.name if alert.patient else "-",
            "message": alert.message,
            "status": alert.status,
            "created_at": alert.created_at.strftime("%d %b %H:%M"),
            "location": alert.location
        })

    # ======================
    # TODAY SCHEDULE
    # ======================
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    today_schedule = []

    for duty in NurseDuty.objects(
        duty_end__gte=today_start,
        duty_start__lt=today_end
    ).select_related():
        if not hospital_id or duty.nurse.user in hospital_users:
            today_schedule.append(
                f"Nurse duty ({duty.shift}) at {duty.duty_start.strftime('%H:%M')}"
            )

    for visit in DoctorVisit.objects(
        visit_time__gte=today_start,
        visit_time__lt=today_end
    ).select_related():
        if not hospital_id or visit.patient.user in hospital_users:
            today_schedule.append(
                f"Doctor visit at {visit.visit_time.strftime('%H:%M')}"
            )

    # ======================
    # CHART DATA
    # ======================
    chart_labels = []
    chart_values = []

    current_day = start_date
    while current_day < end_date:
        next_day = current_day + timedelta(days=1)

        count = PatientProfile.objects(
            patient_filter,
            service_start__gte=current_day.date(),
            service_start__lt=next_day.date()
        ).count()

        chart_labels.append(current_day.strftime("%d %b"))
        chart_values.append(count)
        current_day = next_day
    # ======================
    # PENDING BILLING
    # ======================. 
    
    pending_bills = PatientBill.objects(
    status__ne="PAID"
    ).only("grand_total")
    # ======================
    # RESPONSE
    # ======================
    total_pending_billing = sum(b.grand_total or 0 for b in pending_bills)
    totalCareTakers = NurseProfile.objects(
        nurse_type="CARETAKER",
        **user_filter
    ).count()
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "hospitals": hospitals,
            "doctors": DoctorProfile.objects(available=True).count(),
            "selected_hospital": hospital_id,
            "total_patients": total_patients,
            "discharged_patients": discharged_patients,
            "active_nurses": total_nurses,
            "total_doctors": total_doctors,
            "monthly_revenue": round(monthly_revenue, 2),
            "recent_activity": recent_activity,
            "sos_alerts": sos_alerts,
            "today_schedule": today_schedule,
            "chart_labels": chart_labels,
            "chart_values": chart_values,
            "start": start,
            "end": end,
            "in_used_equipment": UserEquipmentRequest.objects(status=True).count(),
            "pending_Payments": round(total_pending_billing, 2),
            "total_caretakers": totalCareTakers
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
    admin_users = User.objects(role="ADMIN").order_by("-created_at")
    menu_modules = [module for module in ADMIN_MODULES if module.show_in_menu]
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "admin_users": admin_users,
            "admin_modules": menu_modules,
        }
    )


@router.post("/users/create")
def create_admin_user(
    name: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    admin_role_name: str = Form(...),
    email: str | None = Form(None),
    permissions: List[str] = Form([]),
    current_user=Depends(admin_required)
):
    if not permissions:
        raise HTTPException(400, "Select at least one permission")

    allowed_permissions = {module.key for module in ADMIN_MODULES}
    clean_permissions = [p for p in permissions if p in allowed_permissions]
    if not clean_permissions:
        raise HTTPException(400, "Invalid permissions")

    try:
        User(
            role="ADMIN",
            name=name,
            phone=phone,
            email=email or None,
            password_hash=password,
            admin_role_name=admin_role_name,
            admin_permissions=clean_permissions,
            otp_verified=True,
            is_active=True,
            created_at=datetime.utcnow(),
        ).save()
    except NotUniqueError:
        raise HTTPException(400, "Phone number already exists")

    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/update")
def update_admin_user(
    user_id: str,
    name: str = Form(...),
    admin_role_name: str = Form(...),
    email: str | None = Form(None),
    password: str | None = Form(None),
    permissions: List[str] = Form([]),
    current_user=Depends(admin_required)
):
    user = User.objects(id=user_id, role="ADMIN").first()
    if not user:
        raise HTTPException(404, "Admin user not found")

    if str(user.id) == str(current_user.id) and not permissions:
        raise HTTPException(400, "You cannot remove your own access")

    allowed_permissions = {module.key for module in ADMIN_MODULES}
    clean_permissions = [p for p in permissions if p in allowed_permissions]
    if not clean_permissions:
        raise HTTPException(400, "Select at least one permission")

    user.name = name
    user.email = email or None
    user.admin_role_name = admin_role_name
    user.admin_permissions = clean_permissions
    if password:
        user.password_hash = password
        user.token_version += 1
    user.save()

    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle")
def toggle_admin_user(
    user_id: str,
    current_user=Depends(admin_required)
):
    user = User.objects(id=user_id, role="ADMIN").first()
    if not user:
        raise HTTPException(404, "Admin user not found")
    if str(user.id) == str(current_user.id):
        raise HTTPException(400, "You cannot deactivate yourself")

    user.is_active = not user.is_active
    user.token_version += 1
    user.save()

    return RedirectResponse("/admin/users", status_code=303)
@router.get("/create/nurse", response_class=HTMLResponse)
def create_nurse(request: Request):
    return templates.TemplateResponse(
        "admin/nurse_create.html", {"request": request}
    )


@router.get("/create/patient", response_class=HTMLResponse)
def create_patient_page(request: Request):

    doctors = DoctorProfile.objects(available=True)
    hospitals = HospitalModel.objects.all()
    nurses = NurseProfile.objects()

    return templates.TemplateResponse(
        "admin/add_pataint.html",
        {
            "request": request,
            "doctors": doctors,
            "nurses": nurses,
            "hospitals": hospitals,
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
    search: str | None = None,
    user = Depends(role_required(["ADMIN", "NURSE"]))
):
    nurses_query = Q(created_by="ADMIN")

    if search:
        matched_users = User.objects(
            Q(role="NURSE") &
            (
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
        )
        nurses_query &= Q(user__in=matched_users)

    nurses_qs = NurseProfile.objects(nurses_query).select_related()

    return templates.TemplateResponse(
        "admin/nurses.html",
        {
            "request": request,
            "nurses": nurses_qs,
            "search": search or ""
        }
    )


@router.get("/nurses/blocked", response_class=HTMLResponse)
def blocked_nurses(
    request: Request,
    search: str | None = None,
    admin=Depends(admin_required)
):
    blocked_user_query = Q(role="NURSE", is_active=False)

    if search:
        blocked_user_query &= (
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )

    blocked_users = User.objects(blocked_user_query)

    nurses_qs = NurseProfile.objects(
        user__in=blocked_users,
        nurse_type__ne="CARETAKER"
    ).select_related()

    return templates.TemplateResponse(
        "admin/blocked_nurses.html",
        {
            "request": request,
            "nurses": nurses_qs,
            "search": search or ""
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
    status: str = Query("all", pattern="^(all|active|discharged)$"),
    user = Depends(role_required(["ADMIN", "NURSE", "DOCTOR", "PATIENT"]))
):
    ensure_patient_profiles_for_registered_users()

    patient_filter = admin_patient_filter()

    total_patients = PatientProfile.objects(patient_filter).count()
    active_patients = PatientProfile.objects(
        patient_filter,
        service_end=None
    ).count()
    discharged_patients = PatientProfile.objects(
        patient_filter,
        service_end__exists=True,
        service_end__ne=None
    ).count()

    if status == "active":
        patients_qs = PatientProfile.objects(
            patient_filter,
            service_end=None
        ).select_related()
    elif status == "discharged":
        patients_qs = PatientProfile.objects(
            patient_filter,
            service_end__exists=True,
            service_end__ne=None
        ).select_related()
    else:
        patients_qs = PatientProfile.objects(patient_filter).select_related()

    return templates.TemplateResponse(
        "admin/patients.html",
        {
            "request": request,
            "patients": patients_qs,
            "status": status,
            "total_patients": total_patients,
            "active_patients": active_patients,
            "discharged_patients": discharged_patients,
        }
    )


@router.post("/patient/{patient_id}/discharge")
def discharge_patient(
    patient_id: str,
    user = Depends(role_required(["ADMIN", "NURSE"]))
):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if not patient.service_end:
        patient.service_end = date.today()
        patient.save()

    NurseDuty.objects(patient=patient, is_active=True).update(is_active=False)

    return {
        "success": True,
        "message": "Patient closed successfully",
        "service_end": patient.service_end.isoformat()
    }



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
def billing(
    request: Request,
    user=Depends(role_required(["ADMIN"]))
):
    patients_qs = (
        PatientProfile.objects(admin_patient_filter())
        .order_by("user")
        .select_related()
    )

    total_billed = sum(
        bill.grand_total or 0 for bill in PatientBill.objects.only("grand_total")
    )
    total_paid = sum(
        bill.grand_total or 0
        for bill in PatientBill.objects(status="PAID").only("grand_total")
    )
    total_due = sum(
        bill.grand_total or 0
        for bill in PatientBill.objects(status__ne="PAID").only("grand_total")
    )

    return templates.TemplateResponse(
        "admin/billing.html",
        {
            "request": request,
            "patients": patients_qs,
            "total_billed": round(total_billed, 2),
            "total_paid": round(total_paid, 2),
            "total_due": round(total_due, 2),
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
    # print("SOS Alerts Count:", sos_qs.to_json())
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
    # print("Phone:", user.phone)
    # print("Other Number:", user.other_number)
    # print("Email:", user.email)
    # print("Role:", user.role)

    # print("\n--- NURSE PROFILE ---")
    # print("Type:", nurse.nurse_type)
    # print("Aadhaar:", nurse.aadhaar_number)
    # print("Verified:", nurse.verification_status)
    # print("Police Verification:", nurse.police_verification_status)
    # print("PoliceDoc:", nurse.police)
    # print("Joining:", nurse.joining_date)
    # print("Resignation:", nurse.resignation_date)
    # print("Qualification Docs:", nurse.qualification_docs)
    # print("Experience Docs:", nurse.experience_docs)
    print("Profile Photo:",  nurse.digital_signature)

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
            "consent": consent,
            "ist_offset": timedelta(hours=5, minutes=30),
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
    hospitals = HospitalModel.objects.all()
    return templates.TemplateResponse(
        "admin/nurse_edit.html",
        {
            "request": request,
            "nurse": nurse,
            "patients": patients,
            "duties": duties,
            "visits": visits,
            "consent": consent,
            "hospitals": hospitals,

        }
    )


@router.get("/create/doctor", response_class=HTMLResponse)
def doctor_create_page(request: Request):
    hospitals = HospitalModel.objects.all()
    return templates.TemplateResponse(
        "admin/doctor_create.html",
        {
         "request": request,
         "hospitals": hospitals
        }
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

    hospitals = HospitalModel.objects.all()
    return templates.TemplateResponse(
        "admin/doctor_edit.html",
        {
            "request": request,
            "doctor": doctor,
            "hospitals": hospitals,
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
    hospitals = HospitalModel.objects.all()
    visits = NurseVisit.objects(patient=patient).order_by("-visit_time")

    print(patient.to_json())

    return templates.TemplateResponse(
        "admin/edit_patient.html",
        {
            "request": request,
            "patient": patient,
            "doctor": patient.assigned_doctor,
            "nurses": nurses,
            "visits":visits,
            "duties": duties,
            "notes": notes,
            "vitals": vitals,
            "hospitals": hospitals,
        }
    )


# @router.get("/patient/{patient_id}/view", response_class=HTMLResponse)
# def view_patient_details(request: Request, patient_id: str):
#     patient = PatientProfile.objects(id=patient_id).first()
#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")

#     nurses = NurseProfile.objects()
#     duties = NurseDuty.objects(patient=patient, is_active=True)
#     notes = PatientDailyNote.objects(patient=patient).order_by("-created_at")
#     vitals = PatientVitals.objects(patient=patient).order_by("-recorded_at")
#     medications = PatientMedication.objects(patient=patient)
#     relatives = RelativeAccess.objects(patient=patient)
#     relatives = RelativeAccess.objects(patient=patient)
#     all_users = User.objects(role="RELATIVE")
    
#     return templates.TemplateResponse(
#         "admin/view_patient.html",
#         {
#             "request": request,
#             "patient": patient,
#             "doctor": patient.assigned_doctor,
#             "nurses": nurses,
#             "duties": duties,
#             "notes": notes,
#             "vitals": vitals,
#             "medications": medications,
#             "relatives": relatives,
#             "relatives": relatives,
#         }
#     )

@router.get("/patient/{patient_id}/view", response_class=HTMLResponse)
def view_patient_details(request: Request, patient_id: str):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
 
    duties = NurseDuty.objects(patient=patient).order_by("-duty_start")
    notes = PatientDailyNote.objects(patient=patient).order_by("-created_at")
    vitals = PatientVitals.objects(patient=patient).order_by("-recorded_at")
    medications = PatientMedication.objects(patient=patient).order_by("-id")
    relatives = RelativeAccess.objects(patient=patient)
 
    # ── Equipment ──────────────────────────────────────────────
    equipment_requests = UserEquipmentRequest.objects(patient=patient)
 
    equipment_data = []
    total_equipment_cost = 0.0
 
    for eq_req in equipment_requests:
        try:
            equip       = eq_req.equipment          # ReferenceField → EquipmentTable
            days        = eq_req.day_duration or 1
            price_per_day = eq_req.price_per_day or equip.price or 0.0
            total_cost  = days * price_per_day
 
            total_equipment_cost += total_cost
 
            equipment_data.append({
                "title"        : equip.title,
                "image"        : equip.image,
                "price_per_day": price_per_day,
                "days"         : days,
                "total_cost"   : total_cost,
                "status"       : eq_req.status,   # True/False (approved/pending)
            })
        except Exception:
            # Agar reference broken ho toh skip karo
            continue
    # ───────────────────────────────────────────────────────────
 
    return templates.TemplateResponse(
        "admin/view_patient.html",
        {
            "request"              : request,
            "patient"              : patient,
            "doctor"               : patient.assigned_doctor,
            "duties"               : duties,
            "notes"                : notes,
            "vitals"               : vitals,
            "medications"          : medications,
            "relatives"            : relatives,
            # ✅ NEW
            "equipment_data"       : equipment_data,
            "total_equipment_cost" : total_equipment_cost,
            "ist_offset"           : timedelta(hours=5, minutes=30),
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
def staff_manage_page(
    request: Request,
    search: str | None = None
):
    staff_query = Q(role="STAFF")

    if search:
        staff_query &= (
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )

    staff = User.objects(staff_query).order_by("-created_at")
    return templates.TemplateResponse(
        "admin/staff_manage.html",
        {
            "request": request,
            "staff": staff,
            "search": search or ""
        }
    )

@router.get("/hospital", response_class=HTMLResponse)
def hospital_page(request: Request):
    return templates.TemplateResponse(
        "admin/hospitals.html",
        {"request": request}
    )


@router.get("/equipment")
def equipment_page(request: Request):
    return templates.TemplateResponse(
        "admin/equipment.html",
        {"request": request}
    )

@router.get("/request-equipment")
def equipment_page(request: Request):
    return templates.TemplateResponse(
        "admin/equipment_requests.html",
        {"request": request}
    )

@router.get("/payments", response_class=HTMLResponse)
async def admin_payments_page(
    request: Request,
  
):
    payments = (
    AllPaymentsHistory.objects
    
    .order_by("-id")
)


    return templates.TemplateResponse(
        "admin/payments.html",
        {
            "request": request,
            "payments": payments
        }
    )

# care tacker ====================================
@router.get("/create/caretacker", response_class=HTMLResponse)
def create_nurse(request: Request):
    return templates.TemplateResponse(
        "admin/create_caretacker.html", {"request": request}
    )

@router.get("/caretacker/{nurse_id}")
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
    # print("Phone:", user.phone)
    # print("Other Number:", user.other_number)
    # print("Email:", user.email)
    # print("Role:", user.role)

    # print("\n--- NURSE PROFILE ---")
    # print("Type:", nurse.nurse_type)
    # print("Aadhaar:", nurse.aadhaar_number)
    print(" Aadhaar Verified:", nurse.aadhaar_verified)
    # print("Police Verification:", nurse.police_verification_status)
    # print("PoliceDoc:", nurse.police)
    # print("Joining:", nurse.joining_date)
    # print("Resignation:", nurse.resignation_date)
    # print("Qualification Docs:", nurse.qualification_docs)
    # print("Experience Docs:", nurse.experience_docs)
    print("Profile Photo:",  nurse.digital_signature)

    print("========================================\n")

    return templates.TemplateResponse(
        "admin/caretacker_detetail.html",
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
            "consent": consent,
            "ist_offset": timedelta(hours=5, minutes=30),
        }
    )

@router.get("/caretacker/{nurse_id}/edit", response_class=HTMLResponse)
def edit_nurse(nurse_id: str, request: Request):
    nurse = NurseProfile.objects(id=nurse_id).first()
    if not nurse:
        raise HTTPException(404, "Nurse not found")

    patients = PatientProfile.objects()
    duties = NurseDuty.objects(nurse=nurse, is_active=True).order_by("-duty_start")
    visits = NurseVisit.objects(nurse=nurse).order_by("-visit_time")[:10]
    consent = NurseConsent.objects(nurse=nurse).order_by("-created_at").first()
    hospitals = HospitalModel.objects.all()
    return templates.TemplateResponse(
        "admin/caretacker_edit.html",
        {
            "request": request,
            "nurse": nurse,
            "patients": patients,
            "duties": duties,
            "visits": visits,
            "consent": consent,
            "hospitals": hospitals,

        }
    )


@router.get("/caretacker", response_class=HTMLResponse)
def nurses(
    request: Request,
    search: str | None = None,
    user = Depends(role_required(["ADMIN", "NURSE"]))
):
    nurses_query = Q(nurse_type="CARETAKER")

    if search:
        matched_users = User.objects(
            Q(role="NURSE") &
            (
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
        )
        nurses_query &= Q(user__in=matched_users)

    nurses_qs = NurseProfile.objects(nurses_query).select_related()

    return templates.TemplateResponse(
        "admin/careTacker.html",
        {
            "request": request,
            "nurses": nurses_qs,
            "search": search or ""
        }
    )
