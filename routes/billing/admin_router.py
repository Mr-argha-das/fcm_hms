
from core.paths import BASE_DIR
from core.site_settings import get_site_settings, media_file_path
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse
from core.dependencies import admin_required, get_current_user
from models import BillItem, NurseDuty, PatientInvoice, PatientMedication, PatientProfile, PatientBill, PatientVitals, UserEquipmentRequest
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
import os
import re
from xml.sax.saxutils import escape


import os

router = APIRouter(prefix="/billing", tags=["Billing"])


def pdf_text(value, default="-"):
    text = str(value or default)
    return escape(text).replace("\n", "<br/>")


def get_bill_invoice(bill):
    if getattr(bill, "invoice", None):
        return bill.invoice

    invoice = PatientInvoice.objects(
        patient=bill.patient,
        total_amount=bill.grand_total
    ).order_by("-created_at").first()

    return invoice


# =====================================================
# PDF GENERATOR
# =====================================================


def generate_bill_pdf(bill, gst_percent: float = 0):
    from models import PatientVitals
    import os

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER ,TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Image,
        Spacer
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    # =====================================================
    # FILE SETUP
    # =====================================================

    media_bills_dir = os.path.join(BASE_DIR, "media", "bills")
    os.makedirs(media_bills_dir, exist_ok=True)

    suffix = "gst" if gst_percent > 0 else "nogst"
    path = os.path.join(media_bills_dir, f"bill_{bill.id}_{suffix}.pdf")

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=25,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()
    elements = []  # 🔥 MUST BE FIRST


  # =====================================================
    # 🟢 HEADER (FULL WIDTH LOGO + DETAILS)
    # =====================================================

    site_settings = get_site_settings()
    logo_path = media_file_path(site_settings.logo_path) or os.path.join(BASE_DIR, "media", "logos", "wecare_header.png")

    logo = ""
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=2 * inch, height=1 * inch)


    header_style = ParagraphStyle(
        "header",
        fontSize=8,
        leading=12,
        alignment=TA_RIGHT
    )

    company_lines = [
        f"<b><font size=11>{pdf_text(site_settings.company_name, 'sridevimatka')}</font></b>",
        pdf_text(site_settings.address, ""),
        f"Phone no.: {pdf_text(site_settings.phone, '-')} | Email: {pdf_text(site_settings.email, '-')}",
        f"{pdf_text(site_settings.company_name, 'sridevimatka')}: {pdf_text(site_settings.account_number, '-')}",
        f"GST Number : {pdf_text(site_settings.gst_number, '-')}",
    ]
    company_info = Paragraph(
        "<br/>".join(line for line in company_lines if line and line != "<br/>"),
        header_style
    )


    # 🔥 FULL WIDTH MAGIC
    PAGE_WIDTH = A4[0] - 60

    logo_w = PAGE_WIDTH * 0.18
    info_w = PAGE_WIDTH * 0.82

    header_table = Table(
        [[logo, company_info]],
        colWidths=[logo_w, info_w]  
    )

    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),

        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))

    elements.append(header_table)


    # ---------- TOP LINE ----------
    PAGE_WIDTH = A4[0] - 60


    # top_line = Table([[""]], colWidths=[PAGE_WIDTH])
    # top_line.setStyle(TableStyle([
    #     ("LINEABOVE", (-4, -4), (-1, -1), 1, colors.green),
    # ]))

    # elements.append(top_line)


    # ---------- TITLE (tight spacing) ----------
    title_style = ParagraphStyle(
        "invoice_title",
        alignment=TA_CENTER,
        fontSize=12,
        textColor=colors.green,
        leading=2,        # tight line height
        spaceBefore=2,     # 🔥 very small gap
        spaceAfter=2       # 🔥 very small gap
    )

    elements.append(Paragraph("<b>Tax Invoice</b>", title_style))


    # ---------- BOTTOM LINE ----------
    bottom_line = Table([[""]], colWidths=[PAGE_WIDTH])
    bottom_line.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 1, colors.green),
    ]))

    elements.append(bottom_line)

    elements.append(Spacer(1, 8)) 


    # =====================================================
    # 🟢 PATIENT DETAILS (FULL WIDTH 2-COLUMN)
    # =====================================================
    patient = bill.patient
    bill_date = getattr(bill, "created_at", None)

    date_str = bill_date.strftime("%d-%m-%Y") if bill_date else "-"

    # 🔥 IST TIME (+5:30)
    from datetime import timedelta

    if bill_date:
        ist_time = bill_date + timedelta(hours=5, minutes=30)
        time_str = ist_time.strftime("%I:%M %p")
    else:
        time_str = "-"


    # 🔥 INVOICE NUMBER
    invoice = get_bill_invoice(bill)
    invoice_no_str = invoice.invoice_no if invoice else "-"


    left_style = ParagraphStyle("left", fontSize=8.5, leading=14)
    right_style = ParagraphStyle("right", fontSize=8.5, leading=14, alignment=TA_RIGHT)

    left_block = Paragraph(f"""
    <b>Bill To</b><br/>
    <b>{patient.user.name or "-"}</b><br/>
    {patient.address or "-"}<br/>
    Contact No.: {patient.user.phone or "-"}
    """, left_style)

    right_block = Paragraph(f"""
    <b>Invoice Details</b><br/>
    Invoice No: {invoice_no_str}<br/>
    Date: {date_str}<br/>
    Time: {time_str}<br/>
    """, right_style)


    # 🔥 REAL FULL WIDTH
    PAGE_WIDTH = A4[0] - 60   # same margins as doc (30+30)

    left_w = PAGE_WIDTH * 0.6
    right_w = PAGE_WIDTH * 0.4

    details_table = Table(
        [[left_block, right_block]],
        colWidths=[left_w, right_w]   # ✅ dynamic width used
    )

    details_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(details_table)
    elements.append(Spacer(1, 12))


    
    # =====================================================
    # PATIENT VITALS TABLE
    # =====================================================

    # vitals_qs = (
    #     PatientVitals.objects(patient=patient)
    #     .order_by("-recorded_at")[:10]
    # )

    #     # ---------- TITLE (tight spacing) ----------
    # chart_style = ParagraphStyle(
    #     "invoice_title",
    #     alignment=TA_CENTER,
    #     fontSize=10,
    #     textColor=colors.green,
    #     leading=14,        # tight line height
    #     spaceBefore=2,     # 🔥 very small gap
    #     spaceAfter=2       # 🔥 very small gap
    # )

    # elements.append(Paragraph("<b>Patient Vitals Chart</b>",chart_style))

    # # ParagraphStyle(
    # #     "center_heading",   # ✅ style name REQUIRED
    # #     parent=styles["Heading4"],
    # #     alignment=TA_CENTER,
    # #     fontSize=13
    # # )
    # if vitals_qs:

    #     table_data = [[
    #         "Time", "BP", "SpO2", "Pulse", "Temp", "O2", "RBS",
    #         "BiPAP", "IV", "Suction", "Feeding", "Urine", "Stool", "Other"
    #     ]]

    #     for v in vitals_qs:
    #         table_data.append([
    #             v.recorded_at.strftime("%I:%M %p") if v.recorded_at else "-",
    #             v.bp or "-",
    #             v.spo2 or "-",
    #             v.pulse or "-",
    #             v.temperature or "-",
    #             v.o2_level or "-",
    #             v.rbs or "-",
    #             v.bipap_ventilator or "-",
    #             v.iv_fluids or "-",
    #             v.suction or "-",
    #             v.feeding_tube or "-",
    #             v.urine or "-",
    #             v.stool or "-",
    #             v.other or "-",
    #         ])

    #     PAGE_WIDTH = A4[0] - 60
    #     col_width = PAGE_WIDTH / 14

    #     vitals_table = Table(
    #         table_data,
    #         colWidths=[col_width] * 14,
    #         repeatRows=1
    #     )

    #     vitals_table.setStyle(TableStyle([
    #         ("GRID", (0, 0), (-1, -1), 0.6, colors.white),
    #         ("BACKGROUND", (0, 0), (-1, 0), colors.green),
    #         ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
    #         ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    #         ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    #     ]))


    #     elements.append(vitals_table)

    # else:
    #     elements.append(Paragraph("No vitals recorded.", styles["Normal"]))

    # elements.append(Spacer(1, 14))


    # =====================================================
    # 🟢 ITEMS TABLE (FULL WIDTH)
    # =====================================================

    items_data = [[
        "S.No.",
        "Services/Equipment",
        "Start",
        "Till",
        "Days",
        "Qty",
        "Unit",
        # "Base",
        "GST%",
        "GST Amt",
        "Total"
    ]]
    for idx, item in enumerate(bill.items, 1):

        start = item.start_date.strftime("%d-%m-%y") if item.start_date else "-"
        till = item.till_date.strftime("%d-%m-%y") if item.till_date else "-"

        items_data.append([
            idx,
            item.title,
            start,
            till,
            item.days or "-",
            item.quantity,
            f"{item.unit_price:.2f}",
            # f"{item.base_total:.2f}",
            f"{item.gst_percent:.0f}%",
            f"{item.gst_amount:.2f}",
            f"{item.total_price:.2f} Rs"
        ])


    # 🔥 FULL WIDTH MAGIC
    PAGE_WIDTH = A4[0] - 60

    col_widths = [
        PAGE_WIDTH * 0.06,  # #
        PAGE_WIDTH * 0.36,  # Service
        PAGE_WIDTH * 0.08,  # Start
        PAGE_WIDTH * 0.08,  # Till
        PAGE_WIDTH * 0.05,  # Days
        PAGE_WIDTH * 0.05,  # Qty
        PAGE_WIDTH * 0.08,  # Unit
        # PAGE_WIDTH * 0.10,  # Base
        PAGE_WIDTH * 0.06,  # GST%
        PAGE_WIDTH * 0.08,  # GST Amt
        PAGE_WIDTH * 0.10,  # Total
    ]

    items_table = Table(
        items_data,
        colWidths=col_widths,
        repeatRows=1
    )

    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.green),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
         # 🔥 horizontal lines only
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.lightgrey),
         # 🔹 HEADER padding fix
        ("LEFTPADDING", (0, 0), (0, 0), 6),

           # ---------- HEADER ----------
        ("ALIGN", (0, 0), (0, 0), "RIGHT"),   # #
        ("ALIGN", (1, 0), (1, 0), "LEFT"),     # Service
        ("ALIGN", (2, 0), (2, 0), "CENTER"),   # Start Date
        ("ALIGN", (3, 0), (3, 0), "CENTER"),   # Till Date
        ("ALIGN", (4, 0), (4, 0), "CENTER"),   # Days
        ("ALIGN", (5, 0), (5, 0), "CENTER"),   # Qty
        ("ALIGN", (6, 0), (6, 0), "CENTER"),   # Unit
        ("ALIGN", (7, 0), (7, 0), "CENTER"),   # Unit
        ("ALIGN", (8, 0), (8, 0), "CENTER"),   # Unit
        ("ALIGN", (9, 0), (9, 0), "RIGHT"),    # Amount

        # ---------- BODY ----------
        ("ALIGN", (0, 1), (0, -1), "CENTER"),  # #
        ("ALIGN", (1, 1), (1, -1), "LEFT"),    # Service
        ("ALIGN", (2, 1), (2, -1), "CENTER"),  # Start Date
        ("ALIGN", (3, 1), (3, -1), "CENTER"),  # Till Date
        ("ALIGN", (4, 1), (4, -1), "CENTER"),  # Days
        ("ALIGN", (5, 1), (5, -1), "CENTER"),  # Qty
        ("ALIGN", (6, 1), (6, -1), "CENTER"),  # Unit
        ("ALIGN", (7, 1), (7, -1), "CENTER"),  # Unit
        ("ALIGN", (8, 1), (8, -1), "CENTER"),  # Unit
        ("ALIGN", (9, 1), (9, -1), "RIGHT"),   # Amount
    ]))

    elements.append(items_table)
    elements.append(Spacer(1, 5))

    # =====================================================
    # 🟢 BANK DETAILS (LEFT SIDE CLEAN)
    # =====================================================

    qr_path = media_file_path(site_settings.qr_path) or os.path.join(BASE_DIR, "media", "logos", "upi_qr.jpeg")

    qr_img = ""
    if os.path.exists(qr_path):
        qr_img = Image(qr_path, width=1.2 * inch, height=1.2 * inch)

    bank_style = ParagraphStyle(
        "bank",
        fontSize=8,
        leading=14,
        alignment=TA_LEFT   
    )

    # 🔥 thin header
    bank_title = Paragraph(
        "<font color='white'>Bank Details</font>",
        ParagraphStyle(
            "bank_head",
            alignment=TA_LEFT,
            fontSize=8,
            leading=9
        )
    )
    
    bank_lines = [
        f"Name: {pdf_text(site_settings.bank_name, '-')}",
        f"Account No.: {pdf_text(site_settings.account_number, '-')}",
        f"IFSC code: {pdf_text(site_settings.ifsc_code, '-')}",
        f"Pin code: {pdf_text(site_settings.pin_code, '-')}",
        f"Account Holder: {pdf_text(site_settings.account_holder_name, '-')}",
    ]
    if site_settings.upi_id:
        bank_lines.append(f"UPI ID: {pdf_text(site_settings.upi_id)}")
    bank_info = Paragraph("<br/>".join(bank_lines), bank_style)

    # 🔥 inner content table (QR + text)
    bank_content = Table(
        [[qr_img, bank_info]],
        colWidths=[1.3 * inch, PAGE_WIDTH * 0.55 - 1.7 * inch]
    )

    bank_content.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    # 🔥 outer table (header + content)
    bank_table = Table(
        [
            [bank_title],
            [bank_content]
        ],
        colWidths=[PAGE_WIDTH * 0.55]
    )

    bank_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.green),
        # normal body padding
        ("TOPPADDING", (0, 1), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 0),

        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),

        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))



# =====================================================
# 🟢 TOTALS TABLE (ITEM GST + EXTRA GST)
# =====================================================

    # 🔥 already includes item GST
    base_amount = bill.grand_total

    # 🔥 extra GST (download time)
    extra_gst_amount = round((base_amount * gst_percent) / 100, 2)

    final_payable = base_amount + extra_gst_amount
# 🔥 CALCULATE GST FROM ITEMS
    item_gst_total = sum(i.gst_amount or 0 for i in bill.items)

    totals_data = [
        ["Sub Total (Incl. GST) :", f"{bill.sub_total :.2f} Rs"],
        # ["Item GST :", f"{item_gst_total:.2f} Rs"],
        ["Discount :", f"- {bill.discount:.2f} Rs" if bill.discount > 0 else f"{bill.discount:.2f} Rs"],
        ["Extra Charges :", f"{bill.extra_charges:.2f} Rs"],
        ["Total (Before Extra GST) :", f"{base_amount:.2f} Rs"],
    ]

    # totals_data = [
    #     ["Sub Total :", f"{bill.sub_total:.2f} Rs"],
    #     ["Item GST :", f"{bill.total_gst:.2f} Rs"],  # 🔥 show stored GST
    #     ["Discount :", f"{bill.discount:.2f} Rs"],
    #     ["Extra Charges :", f"{bill.extra_charges:.2f} Rs"],
    #     ["Total (Before Extra GST) :", f"{base_amount:.2f} Rs"],
    # ]


    if gst_percent > 0:
        totals_data.extend([
            [f"Extra GST @ {gst_percent}% :", f"{extra_gst_amount:.2f} Rs"],
            ["Total Payable :", f"{final_payable:.2f} Rs"],
        ])
    else:
        totals_data.append(["Total Payable :", f"{base_amount:.2f} Rs"])

    totals_table = Table(
        totals_data,
        colWidths=[PAGE_WIDTH * 0.25, PAGE_WIDTH * 0.20]  # only 2 cols
    )

    totals_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),

        ("FONT", (0, 0), (-1, -2), "Helvetica", 8),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 10),

        ("LINEABOVE", (0, -1), (-1, -1), 1.2, colors.green),
    ]))


    combined_table = Table(
    [[bank_table, totals_table]],
    colWidths=[PAGE_WIDTH * 0.55, PAGE_WIDTH * 0.45]
)

    combined_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    elements.append(combined_table)

#    # =====================================================
#     # 🟢 TOTALS TABLE (FULL WIDTH + RIGHT ALIGNED)
#     # =====================================================

#     gst_amount = round((bill.grand_total * gst_percent) / 100, 2)
#     total_with_gst = bill.grand_total + gst_amount

   
#     totals_data = [
#         ["Sub Total :", f"{bill.sub_total:.2f} Rs"],
#         ["Discount :", f"{bill.discount:.2f} Rs"],
#         ["Extra Charges :", f"{bill.extra_charges:.2f} Rs"],
#         ["Total (Without GST) :", f"{bill.grand_total:.2f} Rs"],
#     ]

#     if gst_percent > 0:
#         totals_data.append([f"GST @ {gst_percent}% :", f"{gst_amount:.2f} Rs"])
#         totals_data.append(["Total Payable :", f"{total_with_gst:.2f} Rs"])


#     totals_table = Table(
#         totals_data,
#         colWidths=[PAGE_WIDTH * 0.25, PAGE_WIDTH * 0.20]  # only 2 cols
#     )

#     totals_table.setStyle(TableStyle([
#         ("ALIGN", (0, 0), (0, -1), "RIGHT"),
#         ("ALIGN", (1, 0), (1, -1), "RIGHT"),

#         ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
#         ("LINEABOVE", (0, -1), (-1, -1), 1, colors.green),
#     ]))

#     combined_table = Table(
#     [[bank_table, totals_table]],
#     colWidths=[PAGE_WIDTH * 0.55, PAGE_WIDTH * 0.45]
# )

#     combined_table.setStyle(TableStyle([
#         ("VALIGN", (0, 0), (-1, -1), "TOP"),
#     ]))

#     elements.append(combined_table)

    # =====================================================
    # FOOTER
    # =====================================================

    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "This is a computer generated bill.",
        ParagraphStyle("footer", alignment=TA_CENTER, fontSize=9)
    ))


    # =====================================================
    # BUILD PDF
    # =====================================================

    doc.build(elements)
    return path




def generate_invoice_no():
    highest = 0
    for invoice in PatientInvoice.objects.only("invoice_no"):
        match = re.fullmatch(r"INV-(\d+)", invoice.invoice_no or "")
        if match:
            highest = max(highest, int(match.group(1)))

    return f"INV-{highest + 1:02d}"


def serialize_bill_item(item, index):
    return {
        "index": index,
        "title": item.title or "",
        "quantity": item.quantity or 1,
        "unit_price": float(item.unit_price or 0),
        "base_total": float(item.base_total or 0),
        "gst_percent": float(item.gst_percent or 0),
        "gst_amount": float(item.gst_amount or 0),
        "total_price": float(item.total_price or 0),
        "start_date": item.start_date.isoformat() if item.start_date else None,
        "till_date": item.till_date.isoformat() if item.till_date else None,
        "days": item.days,
        "dosage": item.dosage,
    }


def sync_bill_invoice_totals(bill):
    invoice = get_bill_invoice(bill)
    if not invoice:
        return

    paid_amount = float(invoice.paid_amount or 0)
    invoice.total_amount = bill.grand_total
    invoice.paid_amount = min(paid_amount, bill.grand_total)
    invoice.due_amount = max(bill.grand_total - invoice.paid_amount, 0)
    invoice.status = "PAID" if invoice.due_amount <= 0 else "DUE"
    invoice.save()
# =====================================================
# GENERATE BILL
# =====================================================

@router.post("/admin/billing/generate")
async def generate_bill(
    request: Request,
    user=Depends(get_current_user)
):
    data = await request.json()

    if user.role != "ADMIN":
        raise HTTPException(403, "Only admin can generate bill")

    try:
        patient = PatientProfile.objects.get(id=data["patient_id"])
    except:
        raise HTTPException(404, "Patient not found")

    items = []
    sub_total = 0

    # =================================================
    # 💊 MEDICINES
    # =================================================
    medicines = PatientMedication.objects(patient=patient)

    for m in medicines:
        if not m.price:
            continue

        qty = m.duration_days or 1
        base_total = qty * m.price

        item = BillItem(
            title=f"Medicine: {m.medicine_name}",
            quantity=qty,
            unit_price=m.price,
            base_total=base_total,
            gst_percent=0,
            gst_amount=0,
            total_price=base_total,
            dosage=m.dosage
        )

        items.append(item)
        sub_total += base_total

    # =================================================
    # 👩‍⚕️ NURSE DUTY (Using is_active)
    # =================================================
    duties = NurseDuty.objects(
        patient=patient,
        is_active=True
    )

    for duty in duties:

        if not duty.price_perday:
            continue

        days = duty.duration_days or 1
        unit_price = duty.price_perday
        base_total = days * unit_price

        nurse_name = (
            duty.nurse.user.name
            if duty.nurse and duty.nurse.user
            else "Nurse"
        )

        item = BillItem(
            title=f"Nurse Duty ({nurse_name}) - {duty.duty_type}",
            quantity=days,
            unit_price=unit_price,
            base_total=base_total,
            gst_percent=0,
            gst_amount=0,
            total_price=base_total,
            start_date=duty.duty_start.date() if duty.duty_start else None,
            till_date=duty.duty_end.date() if duty.duty_end else None,
            days=days
        )

        items.append(item)
        sub_total += base_total

        # 🔥 Prevent duplicate billing
        duty.update(is_active=False)

    # =================================================
    # 🏥 EQUIPMENT (Using status)
    # =================================================
    equipment_requests = UserEquipmentRequest.objects(
        patient=patient,
        status=True
    )

    for req in equipment_requests:

        equipment = req.equipment

        if not equipment:
            continue

        qty = 1
        days = req.day_duration or 1
        assigned_unit_price = req.price_per_day or 0
        monthly_price = req.monthly_price or 0
        unit_price = assigned_unit_price or monthly_price or equipment.price or 0

        if not unit_price and not monthly_price:
            continue

        base_total = (
            days * qty * assigned_unit_price
            if assigned_unit_price > 0
            else (monthly_price or (days * qty * unit_price))
        )
        title_suffix = (
            f"{days} day{'s' if days != 1 else ''} x {assigned_unit_price:.2f}/day"
            if assigned_unit_price > 0
            else (
                f"monthly {monthly_price:.2f}"
                if monthly_price > 0
                else f"{days} day{'s' if days != 1 else ''} x {unit_price:.2f}/day"
            )
        )

        item = BillItem(
            title=f"Equipment: {equipment.title} ({title_suffix})",
            quantity=qty,
            unit_price=unit_price,
            base_total=base_total,
            gst_percent=0,
            gst_amount=0,
            total_price=base_total,
            days=days
        )

        items.append(item)
        sub_total += base_total

        # 🔥 Prevent duplicate billing
        req.update(status=False)

    # =================================================
    # 🧾 OTHER ITEMS
    # =================================================
    for i in data.get("other_items", []):

        title = i.get("title")
        qty = i.get("quantity", 1)
        unit_price = i.get("unit_price", 0)
        days = i.get("days")
        gst_percent = i.get("gst_percent", 0)

        start_date = (
            datetime.strptime(i["start_date"], "%Y-%m-%d").date()
            if i.get("start_date") else None
        )
        till_date = (
            datetime.strptime(i["till_date"], "%Y-%m-%d").date()
            if i.get("till_date") else None
        )

        if days:
            base_total = days * qty * unit_price
        else:
            base_total = qty * unit_price

        gst_amount = base_total * gst_percent / 100
        total_price = base_total + gst_amount

        item = BillItem(
            title=title,
            quantity=qty,
            unit_price=unit_price,
            base_total=base_total,
            gst_percent=gst_percent,
            gst_amount=gst_amount,
            total_price=total_price,
            start_date=start_date,
            till_date=till_date,
            days=days
        )

        items.append(item)
        sub_total += total_price

    # =================================================
    # 💰 TOTALS
    # =================================================
    if not items:
        raise HTTPException(400, "Add at least one billable item")

    discount = max(float(data.get("discount", 0) or 0), 0)
    extra = max(float(data.get("extra_charges", 0) or 0), 0)

    grand_total = max(sub_total - discount + extra, 0)

    bill = PatientBill(
        patient=patient,
        items=items,
        sub_total=sub_total,
        discount=discount,
        extra_charges=extra,
        grand_total=grand_total,
        created_by=user,
        bill_month=datetime.utcnow().strftime("%b %Y"),
        status="UNPAID"
    )

    bill.save()

    # =================================================
    # 🧾 CREATE INVOICE
    # =================================================
    invoice_no = generate_invoice_no()

    invoice = PatientInvoice(
        patient=patient,
        invoice_no=invoice_no,
        total_amount=grand_total,
        paid_amount=0,
        due_amount=grand_total,
        status="DUE"
    )

    invoice.save()
    bill.invoice = invoice
    bill.save()

    return {
        "message": "Bill generated successfully",
        "bill_id": str(bill.id),
        "invoice_no": invoice_no,
        "sub_total": sub_total,
        "grand_total": grand_total
    }
# @router.post("/admin/billing/generate")
# async def generate_bill(
#     request: Request,
#     user=Depends(get_current_user)
# ):
#     data = await request.json()

#     # =================================================
#     # 🔒 ADMIN ONLY
#     # =================================================
#     if user.role != "ADMIN":
#         raise HTTPException(403, "Only admin can generate bill")

#     # =================================================
#     # 🔍 PATIENT
#     # =================================================
#     try:
#         patient = PatientProfile.objects.get(id=data["patient_id"])
#     except:
#         raise HTTPException(404, "Patient not found")

#     items = []
#     sub_total = 0
#     gst_total = 0

#     # =================================================
#     # 💊 MEDICINES AUTO BILLING
#     # =================================================
#     medicines = PatientMedication.objects(patient=patient)

#     for m in medicines:
#         if not m.price:
#             continue

#         qty = m.duration_days or 1
#         base_total = qty * m.price

#         item = BillItem(
#             title=f"Medicine: {m.medicine_name}",
#             quantity=qty,
#             unit_price=m.price,
#             base_total=base_total,
#             gst_percent=0,
#             gst_amount=0,
#             total_price=base_total,
#             dosage=m.dosage
#         )

#         items.append(item)
#         sub_total += base_total

#     # =================================================
#     # 🧾 OTHER ITEMS (WITH GST)
#     # =================================================
#     for i in data.get("other_items", []):

#         title = i.get("title")
#         qty = i.get("quantity", 1)
#         unit_price = i.get("unit_price", 0)
#         days = i.get("days")
#         gst_percent = i.get("gst_percent", 0)

#         start_date = (
#             datetime.strptime(i["start_date"], "%Y-%m-%d").date()
#             if i.get("start_date") else None
#         )
#         till_date = (
#             datetime.strptime(i["till_date"], "%Y-%m-%d").date()
#             if i.get("till_date") else None
#         )

#         # ---------- BASE ----------
#         if days:
#             base_total = days * qty * unit_price
#         else:
#             base_total = qty * unit_price

#         # ---------- GST ----------
#         gst_amount = base_total * gst_percent / 100

#         # ---------- FINAL ----------
#         total = base_total + gst_amount

#         item = BillItem(
#             title=title,
#             quantity=qty,
#             unit_price=unit_price,
#             base_total=base_total,
#             gst_percent=gst_percent,
#             gst_amount=gst_amount,
#             total_price=total,
#             start_date=start_date,
#             till_date=till_date,
#             days=days
#         )

#         items.append(item)

#         sub_total += base_total
#         gst_total += gst_amount

#     # =================================================
#     # 💰 TOTALS
#     # =================================================
#     discount = data.get("discount", 0)
#     extra = data.get("extra_charges", 0)

#     grand_total = max(sub_total + gst_total - discount + extra, 0)

#     # =================================================
#     # 💾 SAVE
#     # =================================================
#     bill = PatientBill(
#         patient=patient,
#         items=items,
#         sub_total=sub_total,
#         gst_total=gst_total,
#         discount=discount,
#         extra_charges=extra,
#         grand_total=grand_total,
#         created_by=user,
#         bill_month=datetime.utcnow().strftime("%b %Y"),
#         status="UNPAID"
#     )

#     bill.save()

#     return {
#         "message": "Bill generated successfully",
#         "bill_id": str(bill.id),
#         "sub_total": sub_total,
#         "gst_total": gst_total,
#         "grand_total": grand_total
#     }

# =====================================================
# DOWNLOAD BILL (GST / NON-GST)
# =====================================================

# Neww
@router.get("/admin/billing/{bill_id}/download", response_model=None)
def download_bill_pdf(
    bill_id: str,
    gst_percent: float = Query(0, ge=0, le=100),
    admin=Depends(admin_required),
):
    bill = PatientBill.objects(id=bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    pdf_path = generate_bill_pdf(
        bill=bill,
        gst_percent=gst_percent
    )

    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=500,
            detail=f"PDF not found at {pdf_path}"
        )

    filename = (
        f"Bill_{bill_id}_GST_{gst_percent}.pdf"
        if gst_percent > 0
        else f"Bill_{bill_id}_No_GST.pdf"
    )

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename
    )

# =====================================================
# GET PATIENT BILLS
# =====================================================
@router.get("/admin/patient/{patient_id}/bills")
def get_patient_bills(
    patient_id: str,
    admin=Depends(admin_required)
):  
    bills = PatientBill.objects(patient=patient_id).order_by("-id")

    response = []

    for b in bills:
        bill_date = getattr(b, "created_at", None)
        date_str = bill_date.strftime("%d-%m-%Y") if bill_date else "-"
        invoice = get_bill_invoice(b)

        response.append({
            "bill_id": str(b.id),
            "invoice_no": invoice.invoice_no if invoice else "-",
            "date": date_str,
            "amount": float(b.grand_total),
            "status": b.status,
            "payment_mode": b.payment_mode,
            "paid_at": b.paid_at.isoformat() if b.paid_at else None,
        })

    return response


@router.get("/admin/billing/{bill_id}")
def get_bill_detail(
    bill_id: str,
    admin=Depends(admin_required)
):
    bill = PatientBill.objects(id=bill_id).first()
    if not bill:
        raise HTTPException(404, "Bill not found")

    invoice = get_bill_invoice(bill)

    return {
        "bill_id": str(bill.id),
        "invoice_no": invoice.invoice_no if invoice else "-",
        "patient_id": str(bill.patient.id) if bill.patient else None,
        "bill_date": bill.created_at.strftime("%Y-%m-%d") if bill.created_at else None,
        "bill_month": bill.bill_month or "",
        "items": [
            serialize_bill_item(item, index)
            for index, item in enumerate(bill.items or [])
        ],
        "sub_total": float(bill.sub_total or 0),
        "discount": float(bill.discount or 0),
        "extra_charges": float(bill.extra_charges or 0),
        "grand_total": float(bill.grand_total or 0),
        "status": bill.status,
        "payment_mode": bill.payment_mode or "",
        "paid_at": bill.paid_at.strftime("%Y-%m-%d") if bill.paid_at else None,
        "invoice_status": invoice.status if invoice else "",
        "paid_amount": float(invoice.paid_amount or 0) if invoice else 0,
        "due_amount": float(invoice.due_amount or 0) if invoice else float(bill.grand_total or 0),
    }


@router.put("/admin/billing/{bill_id}")
async def update_bill(
    bill_id: str,
    request: Request,
    admin=Depends(admin_required)
):
    bill = PatientBill.objects(id=bill_id).first()
    if not bill:
        raise HTTPException(404, "Bill not found")

    data = await request.json()
    items = []
    sub_total = 0.0
    gst_total = 0.0

    for row in data.get("items", []):
        title = (row.get("title") or "").strip()
        if not title:
            continue

        qty = max(int(row.get("quantity") or 1), 1)
        unit_price = max(float(row.get("unit_price") or 0), 0)
        days = row.get("days")
        days = int(days) if days else None
        gst_percent = max(float(row.get("gst_percent") or 0), 0)

        start_date = (
            datetime.strptime(row["start_date"], "%Y-%m-%d").date()
            if row.get("start_date") else None
        )
        till_date = (
            datetime.strptime(row["till_date"], "%Y-%m-%d").date()
            if row.get("till_date") else None
        )

        multiplier = days if days else 1
        base_total = multiplier * qty * unit_price
        gst_amount = base_total * gst_percent / 100
        total_price = base_total + gst_amount

        items.append(BillItem(
            title=title,
            quantity=qty,
            unit_price=unit_price,
            base_total=base_total,
            gst_percent=gst_percent,
            gst_amount=gst_amount,
            total_price=total_price,
            start_date=start_date,
            till_date=till_date,
            days=days,
            dosage=row.get("dosage"),
        ))
        sub_total += total_price
        gst_total += gst_amount

    if not items:
        raise HTTPException(400, "Add at least one billable item")

    discount = max(float(data.get("discount") or 0), 0)
    extra = max(float(data.get("extra_charges") or 0), 0)
    grand_total = max(sub_total - discount + extra, 0)

    bill.items = items
    bill.sub_total = sub_total
    bill.gst_total = gst_total
    bill.total_gst = gst_total
    bill.discount = discount
    bill.extra_charges = extra
    bill.grand_total = grand_total

    if data.get("bill_date"):
        bill.created_at = datetime.strptime(data["bill_date"], "%Y-%m-%d")

    bill.bill_month = (data.get("bill_month") or bill.bill_month or "").strip()

    status = (data.get("status") or bill.status or "UNPAID").upper()
    if status not in ("UNPAID", "PAID"):
        raise HTTPException(400, "Invalid bill status")
    bill.status = status

    payment_mode = (data.get("payment_mode") or "").upper()
    if payment_mode and payment_mode not in ("CASH", "UPI", "BANK", "CARD"):
        raise HTTPException(400, "Invalid payment mode")
    bill.payment_mode = payment_mode or None

    if data.get("paid_at"):
        bill.paid_at = datetime.strptime(data["paid_at"], "%Y-%m-%d")
    elif status == "UNPAID":
        bill.paid_at = None

    invoice = get_bill_invoice(bill)
    if invoice:
        invoice_no = (data.get("invoice_no") or invoice.invoice_no or "").strip()
        if invoice_no:
            existing = PatientInvoice.objects(invoice_no=invoice_no, id__ne=invoice.id).first()
            if existing:
                raise HTTPException(400, "Invoice number already exists")

    bill.save()

    if invoice:
        invoice_no = (data.get("invoice_no") or invoice.invoice_no or "").strip()
        if invoice_no:
            invoice.invoice_no = invoice_no

        paid_amount = max(float(data.get("paid_amount") or 0), 0)
        paid_amount = min(paid_amount, grand_total)
        invoice.total_amount = grand_total
        invoice.paid_amount = paid_amount
        invoice.due_amount = max(grand_total - paid_amount, 0)

        invoice_status = (data.get("invoice_status") or "").upper()
        if invoice_status not in ("PAID", "PARTIAL", "DUE"):
            invoice_status = "PAID" if invoice.due_amount <= 0 else ("PARTIAL" if paid_amount > 0 else "DUE")
        invoice.status = invoice_status
        invoice.save()

    return {
        "message": "Bill updated successfully",
        "bill_id": str(bill.id),
        "sub_total": sub_total,
        "grand_total": grand_total,
    }


@router.get("/admin/bills")
def get_all_bills(
    patient_id: str | None = None,
    status: str | None = Query(None, pattern="^(UNPAID|PAID)$"),
    admin=Depends(admin_required)
):
    filters = {}
    if patient_id:
        filters["patient"] = patient_id
    if status:
        filters["status"] = status

    bills = PatientBill.objects(**filters).order_by("-created_at").select_related()
    response = []

    for bill in bills:
        invoice = get_bill_invoice(bill)
        patient = bill.patient
        user = patient.user if patient else None

        response.append({
            "bill_id": str(bill.id),
            "invoice_no": invoice.invoice_no if invoice else "-",
            "patient_id": str(patient.id) if patient else None,
            "patient_name": user.name if user and user.name else "-",
            "phone": user.phone if user else "-",
            "date": bill.created_at.strftime("%d-%m-%Y") if bill.created_at else "-",
            "amount": float(bill.grand_total or 0),
            "status": bill.status,
            "payment_mode": bill.payment_mode,
            "paid_at": bill.paid_at.isoformat() if bill.paid_at else None,
            "item_count": len(bill.items or []),
        })

    return response


# =====================================================
# MARK BILL PAID
# =====================================================
@router.post("/admin/billing/mark-paid")
def mark_bill_paid(
    bill_id: str,
    payment_mode: str = Query("CASH", pattern="^(CASH|UPI|BANK|CARD)$"),
    admin=Depends(admin_required)
):
    bill = PatientBill.objects(id=bill_id).first()
    if not bill:
        raise HTTPException(404, "Bill not found")

    if bill.status == "PAID":
        return {"message": "Bill already paid"}

    paid_at = datetime.utcnow()
    bill.status = "PAID"
    bill.payment_mode = payment_mode.upper()
    bill.paid_at = paid_at
    bill.save()

    invoice = get_bill_invoice(bill)
    if invoice:
        if not bill.invoice:
            bill.invoice = invoice
            bill.save()
        invoice.status = "PAID"
        invoice.paid_amount = bill.grand_total
        invoice.due_amount = 0
        invoice.save()

    return {
        "message": "Bill marked as PAID",
        "bill_id": str(bill.id),
        "amount": bill.grand_total,
        "payment_mode": bill.payment_mode,
        "paid_at": paid_at
    }


# =====================================================
# DELETE ALL BILLS
# =====================================================
@router.delete("/admin/billing/delete-all")
def delete_all_bills(admin=Depends(admin_required)):
    bills = PatientBill.objects()
    count = bills.count()
    bills.delete()

    return {
        "message": "All bills deleted successfully",
        "deleted_count": count
    }
