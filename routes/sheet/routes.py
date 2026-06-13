from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from io import BytesIO
from datetime import datetime

from models import (
    User, NurseProfile, NurseDuty, NurseAttendance, NurseSalary,
    DoctorProfile, DoctorVisit,
    PatientProfile, PatientVitals, PatientMedication,
    PatientBill, StaffProfile
)

router = APIRouter(prefix="/admin", tags=["Export"])


# ======================================================
# Helper → add sheet
# ======================================================
def add_sheet(wb, name, headers, rows):
    ws = wb.create_sheet(title=name)
    ws.append(headers)

    for r in rows:
        ws.append(r)


# ======================================================
# 🔥 MAIN EXPORT API
# ======================================================
@router.get("/export/excel")
def export_full_excel():

    wb = Workbook()
    wb.remove(wb.active)

    # =====================================
    # USERS (❌ ID removed)
    # =====================================
    rows = []
    for u in User.objects:
        rows.append([
            u.name,
            u.phone,
            u.role,
            u.email,
            u.is_active,
            u.created_at
        ])

    add_sheet(
        wb,
        "Users",
        ["Name", "Phone", "Role", "Email", "Active", "Created"],
        rows
    )

    # =====================================
    # NURSES (❌ ID removed)
    # =====================================
    rows = []
    for n in NurseProfile.objects.select_related():
        rows.append([
            n.user.name,
            n.user.phone,
            n.nurse_type,
            n.verification_status,
            n.joining_date
        ])

    add_sheet(
        wb,
        "Nurses",
        ["Name", "Phone", "Type", "Status", "Joining"],
        rows
    )

    # =====================================
    # PATIENTS (❌ ID removed)
    # =====================================
    rows = []
    for p in PatientProfile.objects.select_related():
        rows.append([
            p.user.name,
            p.user.phone,
            p.age,
            p.gender,
            p.address
        ])

    add_sheet(
        wb,
        "Patients",
        ["Name", "Phone", "Age", "Gender", "Address"],
        rows
    )

    # =====================================
    # DUTY
    # =====================================
    rows = []
    for d in NurseDuty.objects.select_related():
        rows.append([
            d.nurse.user.name if d.nurse else "",
            d.patient.user.name if d.patient else "",
            d.shift,
            d.ward,
            d.room,
            d.duty_start,
            d.duty_end
        ])

    add_sheet(
        wb,
        "NurseDuty",
        ["Nurse", "Patient", "Shift", "Ward", "Room", "Start", "End"],
        rows
    )

    # =====================================
    # VITALS
    # =====================================
    rows = []
    for v in PatientVitals.objects.select_related():
        rows.append([
            v.patient.user.name,
            v.bp,
            v.pulse,
            v.spo2,
            v.temperature,
            v.recorded_at
        ])

    add_sheet(
        wb,
        "Vitals",
        ["Patient", "BP", "Pulse", "SPO2", "Temp", "Time"],
        rows
    )

    # =====================================
    # MEDICATION
    # =====================================
    rows = []
    for m in PatientMedication.objects.select_related():
        rows.append([
            m.patient.user.name,
            m.medicine_name,
            m.dosage,
            ",".join(m.timing),
            m.duration_days,
            m.price
        ])

    add_sheet(
        wb,
        "Medication",
        ["Patient", "Medicine", "Dosage", "Timing", "Days", "Price"],
        rows
    )

    # =====================================
    # BILLS
    # =====================================
    rows = []
    for b in PatientBill.objects.select_related():
        rows.append([
            b.patient.user.name,
            b.bill_month,
            b.sub_total,
            b.gst_total,
            b.discount,
            b.grand_total,
            b.status
        ])

    add_sheet(
        wb,
        "Bills",
        ["Patient", "Month", "SubTotal", "GST", "Discount", "GrandTotal", "Status"],
        rows
    )

    # =====================================
    # DOCTORS
    # =====================================
    rows = []
    for d in DoctorProfile.objects.select_related():
        rows.append([
            d.user.name,
            d.user.phone,
            d.specialization,
            d.experience_years,
            d.available
        ])

    add_sheet(
        wb,
        "Doctors",
        ["Name", "Phone", "Specialization", "Experience", "Available"],
        rows
    )

    # =====================================
    # STAFF
    # =====================================
    rows = []
    for s in StaffProfile.objects.select_related():
        rows.append([
            s.user.name,
            s.user.phone,
            s.staff_type,
            s.joining_date
        ])

    add_sheet(
        wb,
        "Staff",
        ["Name", "Phone", "Type", "Joining"],
        rows
    )

    # =====================================
    # SAVE FILE
    # =====================================
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"hospital_export_{datetime.now().date()}.xlsx"

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
