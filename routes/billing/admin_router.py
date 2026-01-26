# from fastapi import APIRouter, Depends, HTTPException
# from core.dependencies import admin_required, get_current_user
# from models import *
# from reportlab.lib.pagesizes import A4
# from reportlab.pdfgen import canvas
# import os



# def generate_bill_pdf(bill):
#     os.makedirs("media/bills", exist_ok=True)
#     path = f"media/bills/bill_{bill.id}.pdf"

#     c = canvas.Canvas(path, pagesize=A4)
#     w, h = A4
#     y = h - 40

#     c.setFont("Helvetica-Bold", 14)
#     c.drawString(40, y, "PATIENT BILL INVOICE")

#     y -= 30
#     c.setFont("Helvetica", 10)
#     c.drawString(40, y, f"Patient: {bill.patient.user.name}")
#     c.drawString(350, y, f"Date: {bill.bill_date.strftime('%d-%m-%Y')}")

#     y -= 30
#     c.setFont("Helvetica-Bold", 11)
#     c.drawString(40, y, "Billing Items")
#     y -= 20

#     c.setFont("Helvetica", 10)
#     for i in bill.items:
#         c.drawString(40, y, i.title)
#         c.drawRightString(550, y, f"₹ {i.total_price}")
#         y -= 16

#     y -= 15
#     c.drawString(40, y, f"Sub Total: ₹ {bill.sub_total}")
#     y -= 15
#     c.drawString(40, y, f"Discount: ₹ {bill.discount}")
#     y -= 15
#     c.drawString(40, y, f"Extra Charges: ₹ {bill.extra_charges}")

#     y -= 20
#     c.setFont("Helvetica-Bold", 11)
#     c.drawString(40, y, f"TOTAL PAYABLE: ₹ {bill.grand_total}")

#     c.save()
#     return path
# router = APIRouter(prefix="/billing", tags=["Billing"])


# @router.post("/admin/billing/generate")
# def generate_bill(
#     payload: dict,
#     admin=Depends(admin_required)
# ):  
    
# # Example payload:
# #     {
# #   "patient_id": "PATIENT_ID",
# #   "discount": 100,
# #   "extra_charges": 50,
# #   "other_items": [
# #     {
# #       "title": "Emergency Service",
# #       "quantity": 1,
# #       "unit_price": 1000
# #     }
# #   ]
# # }

#     patient = PatientProfile.objects(id=payload["patient_id"]).first()
#     if not patient:
#         raise HTTPException(404, "Patient not found")

#     items = []
#     medicine_list = []

#     # 🔹 MEDICINES FROM PatientMedication
#     meds = PatientMedication.objects(patient=patient)
#     for m in meds:
#         if m.price:
#             items.append(
#                 BillItem(
#                     title=f"Medicine: {m.medicine_name}",
#                     quantity=1,
#                     unit_price=m.price,
#                     total_price=m.price
#                 )
#             )
#             medicine_list.append({
#                 "name": m.medicine_name,
#                 "dosage": m.dosage,
#                 "price": m.price
#             })

#     # 🔹 OTHER BILLING ITEMS
#     for oi in payload.get("other_items", []):
#         total = oi["quantity"] * oi["unit_price"]
#         items.append(
#             BillItem(
#                 title=oi["title"],
#                 quantity=oi["quantity"],
#                 unit_price=oi["unit_price"],
#                 total_price=total
#             )
#         )

#     # 🔢 CALCULATION
#     sub_total = sum(i.total_price for i in items)
#     discount = payload.get("discount", 0)
#     extra = payload.get("extra_charges", 0)

#     grand_total = max(sub_total - discount + extra, 0)

#     bill = PatientBill(
#         patient=patient,
#         items=items,
#         sub_total=sub_total,
#         discount=discount,
#         extra_charges=extra,
#         grand_total=grand_total,
#         bill_month=datetime.utcnow().strftime("%Y-%m"),
#         created_by=admin
#     )
#     bill.save()

#     pdf_path = generate_bill_pdf(bill)
#     bill.pdf_file = pdf_path
#     bill.save()

#     return {
#         "message": "Bill generated successfully",
#         "bill_id": str(bill.id),
#         "patient": patient.user.name,
#         "medicines": medicine_list,
#         "sub_total": sub_total,
#         "grand_total": grand_total,
#         "pdf": pdf_path
#     }


# @router.get("/admin/patient/{patient_id}/bills")
# def get_patient_bills(patient_id: str, admin=Depends(admin_required)):
#     bills = PatientBill.objects(patient=patient_id).order_by("-bill_date")

#     return [
#         {
#             "bill_id": str(b.id),
#             "date": b.bill_date,
#             "amount": b.grand_total,
#             "pdf": b.pdf_file,
#             "status": b.status
#         }
#         for b in bills
#     ]


# @router.post("/admin/billing/mark-paid")
# def mark_bill_paid(
#     bill_id: str,
#     payment_mode: str = "CASH",   # CASH / UPI / BANK
#     admin=Depends(admin_required)
# ):
#     bill = PatientBill.objects(id=bill_id).first()
#     if not bill:
#         raise HTTPException(404, "Bill not found")

#     if bill.status == "PAID":
#         return {"message": "Bill already paid"}

#     bill.status = "PAID"
#     bill.save()

#     return {
#         "message": "Bill marked as PAID",
#         "bill_id": str(bill.id),
#         "amount": bill.grand_total,
#         "payment_mode": payment_mode,
#         "paid_at": datetime.utcnow()
#     }




# @router.delete("/admin/billing/delete-all")
# def delete_all_bills():
#     bills = PatientBill.objects()

#     count = bills.count()
#     bills.delete()

#     return {
#         "message": "All bills deleted successfully",
#         "deleted_count": count
#     }

from core.paths import BASE_DIR
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse
from core.dependencies import admin_required, get_current_user
from models import BillItem, PatientInvoice, PatientMedication, PatientProfile, PatientBill, PatientVitals
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
import os


import os

router = APIRouter(prefix="/billing", tags=["Billing"])


# =====================================================
# PDF GENERATOR
# =====================================================


# def generate_bill_pdf(bill, gst_percent: float = 0):
#     media_bills_dir = os.path.join(BASE_DIR, "media", "bills")
#     os.makedirs(media_bills_dir, exist_ok=True)

#     suffix = "gst" if gst_percent > 0 else "nogst"
#     path = os.path.join(
#         media_bills_dir,
#         f"bill_{bill.id}_{suffix}.pdf"
#     )

#     doc = SimpleDocTemplate(
#         path,
#         pagesize=A4,
#         rightMargin=30,
#         leftMargin=30,
#         topMargin=30,
#         bottomMargin=30
#     )

#     styles = getSampleStyleSheet()
#     elements = []

#     # ================= DATE =================
#     bill_date = getattr(bill, "created_at", None)
#     date_str = bill_date.strftime("%d-%m-%Y") if bill_date else "-"

#     # ================= HEADER IMAGE =================
#     logo_path = os.path.join(BASE_DIR, "media", "logos", "wecare_header.png")
#     if os.path.exists(logo_path):
#         header_img = Image(logo_path, width=3.9 * inch, height=1.4 * inch)
#         header_img.hAlign = "CENTER"
#         elements.append(header_img)

#     elements.append(Paragraph("<br/>", styles["Normal"]))

#     # ================= CONTACT ROW =================
#     contact_row = Table(
#         [[
#             "+91 8432144275",
#             "wcare823@gmail.com",
#             "www.wecarehcs.com"
#         ]],
#         colWidths=[2.3 * inch, 2.3 * inch, 2.4 * inch]
#     )

#     contact_row.setStyle(TableStyle([
#         ("FONT", (0, 0), (-1, -1), "Helvetica-Bold"),
#         ("FONTSIZE", (0, 0), (-1, -1), 9),
#         ("ALIGN", (0, 0), (-1, -1), "CENTER"),
#         ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
#         ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
#         ("TOPPADDING", (0, 0), (-1, -1), 4),
#     ]))

#     elements.append(contact_row)
#     elements.append(Paragraph("<br/>", styles["Normal"]))

#     # ================= PATIENT NAME / DATE =================
#     patient_row = Table(
#         [[
#             f"Patient Name :  {bill.patient.user.name}",
#             f"Date :  {date_str}"
#         ]],
#         colWidths=[5 * inch, 2 * inch]
#     )

#     patient_row.setStyle(TableStyle([
#         ("FONT", (0, 0), (-1, -1), "Helvetica-Bold"),
#         ("FONTSIZE", (0, 0), (-1, -1), 10),
#         ("ALIGN", (0, 0), (0, 0), "LEFT"),
#         ("ALIGN", (1, 0), (1, 0), "RIGHT"),
#         ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
#         ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
#     ]))

#     elements.append(patient_row)
#     elements.append(Paragraph("<br/>", styles["Normal"]))

#     # ================= VITALS TABLE (SAFE VERSION) =================
#     latest_vitals = (
#       PatientVitals.objects(patient=bill.patient)
#       .order_by("-recorded_at")
#       .first()
#     )

#     if latest_vitals:
#      elements.append(Paragraph("<br/>", styles["Normal"]))

#      elements.append(Paragraph(
#         "<b>Patient Vitals</b>",
#         styles["Heading4"]
#     ))

#      vitals_data = [
#         ["BP", latest_vitals.bp or "-"],
#         ["Pulse", latest_vitals.pulse or "-"],
#         ["SpO2", latest_vitals.spo2 or "-"],
#         ["Temperature", latest_vitals.temperature or "-"],
#         ["O2 Level", latest_vitals.o2_level or "-"],
#         ["RBS", latest_vitals.rbs or "-"],
#         ["IV Fluids", latest_vitals.iv_fluids or "-"],
#         ["Suction", latest_vitals.suction or "-"],
#         ["Feeding Tube", latest_vitals.feeding_tube or "-"],
#         ["Urine", latest_vitals.urine or "-"],
#         ["Stool", latest_vitals.stool or "-"],
#         ["Other", latest_vitals.other or "-"],
#         [
#             "Recorded At",
#             latest_vitals.recorded_at.strftime("%d-%m-%Y %I:%M %p")
#             if latest_vitals.recorded_at else "-"
#         ],
#      ]

#      vitals_table = Table(
#         vitals_data,
#         colWidths=[2.5 * inch, 4.5 * inch]
#      )

#      vitals_table.setStyle(TableStyle([
#         ("GRID", (0, 0), (-1, -1), 1, colors.black),
#         ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
#         ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
#         ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
#      ]))

#      elements.append(vitals_table)

#     else:
#     # Optional fallback message
#      elements.append(Paragraph("<br/>No vitals recorded for this patient.<br/>", styles["Normal"]))

   
#     # ================= ITEMS TABLE =================
#     table_data = [["#", "Item", "Qty", "Amount (Rs)"]]

#     for idx, item in enumerate(bill.items, 1):
#       table_data.append([
#         idx,
#         item.title,
#         item.quantity,
#         f"{item.total_price:.2f}",
#     ])

#     items_table = Table(
#         table_data,
#         colWidths=[0.5 * inch, 4.7 * inch, 0.6  * inch, 1.2 * inch]
#     )

#     items_table.setStyle(TableStyle([
#         ("GRID", (0, 0), (-1, -1), 1, colors.black),
#         ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
#         ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
#         ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
#         ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
#     ]))

#     elements.append(items_table)
#     elements.append(Paragraph("<br/>", styles["Normal"]))

#     # ================= TOTALS =================
    # gst_amount = round((bill.grand_total * gst_percent) / 100, 2)
    # total_with_gst = bill.grand_total + gst_amount

    # totals_data = [
    #     ["", "", "Sub Total :", f"{bill.sub_total:.2f} Rs"],
    #     ["", "", "Discount :", f"{bill.discount:.2f} Rs"],
    #     ["", "", "Extra Charges :", f"{bill.extra_charges:.2f} Rs"],
    #     ["", "", "Total (Without GST) :", f"{bill.grand_total:.2f} Rs"],
    # ]

    # if gst_percent > 0:
    #     totals_data.append(
    #         ["", "", f"GST @ {gst_percent}% :", f"{gst_amount:.2f} Rs"]
    #     )
    #     totals_data.append(
    #         ["", "", "Total Payable :", f"{total_with_gst:.2f} Rs"]
    #     )
    
    # totals_table = Table(
    #     totals_data,
    #     colWidths=[0.6 * inch, 3 * inch, 1.2 * inch, 2.2 * inch]
    # )
    
    # totals_table.setStyle(TableStyle([
    #     ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
    #     ("FONT", (2, 0), (-1, -1), "Helvetica-Bold"),
    #     ("FONTSIZE", (0, 0), (-1, -1), 10),
    #     ("TOPPADDING", (0, 0), (-1, -1), 4),
    # ]))
    
    # elements.append(totals_table) 
    
    # # ================= FOOTER =================
    # elements.append(Paragraph("<br/><br/>", styles["Normal"]))
    # elements.append(Paragraph(
    #     "This is a computer generated bill.",
    #      ParagraphStyle("footer", alignment=TA_CENTER, fontSize=9)
    # ))
    
    # doc.build(elements)
    # return path


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

    logo_path = os.path.join(BASE_DIR, "media", "logos", "wecare_header.png")

    logo = ""
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=2.1 * inch, height=.8 * inch)


    header_style = ParagraphStyle(
        "header",
        fontSize=9,
        leading=12,
        alignment=TA_RIGHT
    )

    company_info = Paragraph(
        """
        <b><font size=13>We Care Home Healthcare</font></b><br/>
       432/ 4th floor , Citygate Complex, NEW, Vasna Rd, Shantabag Society,<br/>
         Ahmedabad,<br/>
        Phone no.: 8432144275 | Email: wcare823@gmail.com<br/>
        We Care Home healthcare: 8005220018003441<br/>
        GST Number : 08BLGPN7084P1Z7
        """,
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
    time_str = bill_date.strftime("%I:%M %p") if bill_date else "-"

    # 🔥 SERIAL INVOICE NUMBER (ADD HERE)
    invoice_no = PatientInvoice.objects(
        created_at__lte=bill.created_at
    ).count()

    invoice_no_str = f"INV-{invoice_no:04d}"


    left_style = ParagraphStyle("left", fontSize=9, leading=14)
    right_style = ParagraphStyle("right", fontSize=9, leading=14, alignment=TA_RIGHT)

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
    # PO Date: {date_str}


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

    items_data = [["S.No.", "Services/Equipment","Start Date" , "Till Date" , "Days", "Qty", "Amount"]]

    for idx, item in enumerate(bill.items, 1):
        items_data.append([
            idx,
            item.title,
            item.start_date,
            item.till_date,
            item.days,
            item.quantity,
            f"{item.unit_price:.2f} Rs"
        ])

    # 🔥 FULL WIDTH MAGIC
    PAGE_WIDTH = A4[0] - 60

    col_widths = [
        PAGE_WIDTH * 0.05,  # #
        PAGE_WIDTH * 0.40,  # Services / Equipment
        PAGE_WIDTH * 0.12,  # Start Date
        PAGE_WIDTH * 0.12,  # Till Date
        PAGE_WIDTH * 0.06,  # Days
        PAGE_WIDTH * 0.06,  # Qty
        PAGE_WIDTH * 0.19,  # Amount
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


           # ---------- HEADER ----------
        ("ALIGN", (0, 0), (0, 0), "CENTER"),   # #
        ("ALIGN", (1, 0), (1, 0), "LEFT"),     # Service
        ("ALIGN", (2, 0), (2, 0), "CENTER"),   # Start Date
        ("ALIGN", (3, 0), (3, 0), "CENTER"),   # Till Date
        ("ALIGN", (4, 0), (4, 0), "CENTER"),   # Days
        ("ALIGN", (5, 0), (5, 0), "CENTER"),   # Qty
        ("ALIGN", (6, 0), (6, 0), "RIGHT"),    # Amount

        # ---------- BODY ----------
        ("ALIGN", (0, 1), (0, -1), "CENTER"),  # #
        ("ALIGN", (1, 1), (1, -1), "LEFT"),    # Service
        ("ALIGN", (2, 1), (2, -1), "CENTER"),  # Start Date
        ("ALIGN", (3, 1), (3, -1), "CENTER"),  # Till Date
        ("ALIGN", (4, 1), (4, -1), "CENTER"),  # Days
        ("ALIGN", (5, 1), (5, -1), "CENTER"),  # Qty
        ("ALIGN", (6, 1), (6, -1), "RIGHT"),   # Amount
    ]))

    elements.append(items_table)
    elements.append(Spacer(1, 5))


    # # =====================================================
    # # 🟢 BANK DETAILS (LEFT SIDE)
    # # =====================================================

    # qr_path = os.path.join(BASE_DIR, "media", "logos", "upi_qr.png")

    # qr_img = ""
    # if os.path.exists(qr_path):
    #     qr_img = Image(qr_path, width=1.3 * inch, height=1.3 * inch)

    # bank_style = ParagraphStyle("bank", fontSize=8, leading=12)

    # bank_title = Paragraph(
    #     "<font color='white'>Bank Details</font>",
    #     ParagraphStyle("bank_head", alignment=TA_LEFT, fontSize=8, leftIndent=0)
    # )

    # bank_info = Paragraph("""
    # Name: STATE BANK OF INDIA<br/>
    # Account No.: 44411859276<br/>
    # IFSC code: SBIN0015618<br/>
    # Account Holder: We Care Home Health Care Services
    # """, bank_style)


    # bank_table = Table(
    #     [
    #         [bank_title],
    #         [qr_img, bank_info]
    #     ],
    #     colWidths=[1.5 * inch, PAGE_WIDTH * 0.55 - 1.5 * inch]
    # )

    # bank_table.setStyle(TableStyle([
    #     ("BACKGROUND", (0, 0), (-1, 0), colors.green),
    #     ("VALIGN", (0, 0), (-1, -1), "TOP"),
    #     ("LEFTPADDING", (0, 0), (-1, -1), 6),
    #     ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    # ]))

    # =====================================================
    # 🟢 BANK DETAILS (LEFT SIDE CLEAN)
    # =====================================================

    qr_path = os.path.join(BASE_DIR, "media", "logos", "upi_qr.jpeg")

    qr_img = ""
    if os.path.exists(qr_path):
        qr_img = Image(qr_path, width=1 * inch, height=1 * inch)

    bank_style = ParagraphStyle(
        "bank",
        fontSize=8,
        leading=14,
        alignment=TA_LEFT   # 🔥 force left align
    )

    # 🔥 thin header
    bank_title = Paragraph(
        "<font color='white'>Bank Details</font>",
        ParagraphStyle(
            "bank_head",
            alignment=TA_LEFT,
            fontSize=7,
            leading=10
        )
    )


    
    bank_info = Paragraph("""
    Name: STATE BANK OF INDIA<br/>
    Account No.: 44411859276<br/>
    IFSC code: SBIN0015618<br/>
    Account Holder: We Care Home Health Care Services
    """, bank_style)


    # 🔥 inner content table (QR + text)
    bank_content = Table(
        [[qr_img, bank_info]],
        colWidths=[1.1 * inch, PAGE_WIDTH * 0.55 - 1.7 * inch]
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

        # 🔥 reduce header height
        # ("TOPPADDING", (0, 0), (-1, 0), 3),
        # ("BOTTOMPADDING", (0, 0), (-1, 0), 3),

        # normal body padding
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),

        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),

        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))




   # =====================================================
    # 🟢 TOTALS TABLE (FULL WIDTH + RIGHT ALIGNED)
    # =====================================================

    gst_amount = round((bill.grand_total * gst_percent) / 100, 2)
    total_with_gst = bill.grand_total + gst_amount

    # totals_data = [
    #     ["", "", "Sub Total :", f"{bill.sub_total:.2f} Rs"],
    #     ["", "", "Discount :", f"{bill.discount:.2f} Rs"],
    #     ["", "", "Extra Charges :", f"{bill.extra_charges:.2f} Rs"],
    #     ["", "", "Total (Without GST) :", f"{bill.grand_total:.2f} Rs"],
    # ]

    # if gst_percent > 0:
    #     totals_data.append(["", "", f"GST @ {gst_percent}% :", f"{gst_amount:.2f} Rs"])
    #     totals_data.append(["", "", "Total Payable :", f"{total_with_gst:.2f} Rs"])


    # # 🔥 FULL WIDTH MAGIC
    # PAGE_WIDTH = A4[0] - 60

    # col_widths = [
    #     PAGE_WIDTH * 0.45,   # empty spacer
    #     PAGE_WIDTH * 0.10,   # empty spacer
    #     PAGE_WIDTH * 0.25,   # label
    #     PAGE_WIDTH * 0.20,   # amount
    # ]

    # totals_table = Table(
    #     totals_data,
    #     colWidths=col_widths
    # )

    # totals_table.setStyle(TableStyle([
    #     ("ALIGN", (2, 0), (2, -1), "RIGHT"),   # labels
    #     ("ALIGN", (3, 0), (3, -1), "RIGHT"),   # amounts

    #     ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
    #     ("FONTSIZE", (0, 0), (-1, -1), 8),

    #     ("BOTTOMPADDING", (0, 0), (-1, -1), 3),

    #     # 🔥 highlight final row
    #     ("FONT", (-2, -1), (-1, -1), "Helvetica" , 8),
    #     ("LINEABOVE", (-2, -1), (-1, -1), .5, colors.green),
    # ]))

    totals_data = [
        ["Sub Total :", f"{bill.sub_total:.2f} Rs"],
        ["Discount :", f"{bill.discount:.2f} Rs"],
        ["Extra Charges :", f"{bill.extra_charges:.2f} Rs"],
        ["Total (Without GST) :", f"{bill.grand_total:.2f} Rs"],
    ]

    if gst_percent > 0:
        totals_data.append([f"GST @ {gst_percent}% :", f"{gst_amount:.2f} Rs"])
        totals_data.append(["Total Payable :", f"{total_with_gst:.2f} Rs"])


    totals_table = Table(
        totals_data,
        colWidths=[PAGE_WIDTH * 0.25, PAGE_WIDTH * 0.20]  # only 2 cols
    )

    totals_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),

        ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.green),
    ]))

    combined_table = Table(
    [[bank_table, totals_table]],
    colWidths=[PAGE_WIDTH * 0.55, PAGE_WIDTH * 0.45]
)

    combined_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    elements.append(combined_table)

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

# =====================================================
# GENERATE BILL
# =====================================================
# @router.post("/admin/billing/generate")
# async def generate_bill(
#     request: Request,
#     user=Depends(get_current_user)
# ):
#     data = await request.json()

#     patient = PatientProfile.objects.get(id=data["patient_id"])
    
#     items = []
#     sub_total = 0
#     # ================= MEDICINES =================
#     medicines = PatientMedication.objects(patient=patient)

#     for m in medicines:
#      if m.price:
#         items.append(
#             BillItem(
#                 title=f"Medicine: {m.medicine_name}",
#                 quantity=1,
#                 unit_price=m.price,
#                 total_price=m.price,
#                 dosage=m.dosage
#             )
#         )
#         sub_total += m.price


#     for i in data.get("other_items", []):
#         total = i["quantity"] * i["unit_price"]
#         items.append(
#          BillItem(
#           title=i["title"],
#           quantity=i["quantity"],
#           unit_price=i["unit_price"],
#           total_price=total
#         )
# )
#         sub_total += total

#     discount = data.get("discount", 0)
#     extra = data.get("extra_charges", 0)
#     grand_total = sub_total - discount + extra

#     bill = PatientBill(
#         patient=patient,
#         items=items,
#         sub_total=sub_total,
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
#         "bill_id": str(bill.id)
#     }

@router.post("/admin/billing/generate")
async def generate_bill(
    request: Request,
    user=Depends(get_current_user)
):
    
    data = await request.json()
    print(data)

    # 🔒 Admin only (optional but recommended)
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin can generate bill")

    # 🔍 Safe patient fetch
    try:
        patient = PatientProfile.objects.get(id=data["patient_id"])
    except:
        raise HTTPException(status_code=404, detail="Patient not found")

    items = []
    sub_total = 0

    # ================= MEDICINES =================
    medicines = PatientMedication.objects(patient=patient)

    for m in medicines:
        if not m.price:
            continue

        quantity = m.duration_days or 1
        total = quantity * m.price

        items.append(
            BillItem(
                title=f"Medicine: {m.medicine_name}",
                quantity=quantity,
                unit_price=m.price,
                total_price=total,
                dosage=m.dosage
            )
        )
        sub_total += total

    # ================= OTHER ITEMS =================
    for i in data.get("other_items", []):

        start_date = (
            datetime.strptime(i["start_date"], "%Y-%m-%d").date()
            if i.get("start_date") else None
        )
        till_date = (
            datetime.strptime(i["till_date"], "%Y-%m-%d").date()
            if i.get("till_date") else None
        )

        # ✅ USE DAYS FROM PAYLOAD (if provided)
        days = i.get("days")

        # ✅ USE QUANTITY FROM PAYLOAD (default 1)
        quantity = i.get("quantity", 1)

        unit_price = i.get("unit_price", 0)

        # 🔥 FINAL TOTAL LOGIC
        if days:
            total = days * quantity * unit_price
        else:
            total = quantity * unit_price

        items.append(
            BillItem(
                title=i.get("title"),
                quantity=quantity,
                unit_price=unit_price,
                total_price=total,
                start_date=start_date,
                till_date=till_date,
                days=days
            )
        )

        sub_total += total


    # ================= TOTALS =================
    discount = data.get("discount", 0)
    extra = data.get("extra_charges", 0)

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

    return {
        "message": "Bill generated successfully",
        "bill_id": str(bill.id),
        "sub_total": sub_total,
        "grand_total": grand_total
    }

# =====================================================
# DOWNLOAD BILL (GST / NON-GST)
# =====================================================

# Neww
@router.get("/admin/billing/{bill_id}/download", response_model=None)
def download_bill_pdf(
    bill_id: str,
    gst_percent: float = Query(0, ge=0, le=100),
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
    # admin=Depends(admin_required)
):  
    bills = PatientBill.objects(patient=patient_id).order_by("-id")

    response = []

    for b in bills:
        bill_date = getattr(b, "created_at", None)
        date_str = bill_date.strftime("%d-%m-%Y") if bill_date else "-"

        response.append({
            "bill_id": str(b.id),
            "date": date_str,
            "amount": float(b.grand_total),
            "status": b.status
        })

    return response


# =====================================================
# MARK BILL PAID
# =====================================================
@router.post("/admin/billing/mark-paid")
def mark_bill_paid(
    bill_id: str,
    payment_mode: str = "CASH",
    admin=Depends(admin_required)
):
    bill = PatientBill.objects(id=bill_id).first()
    if not bill:
        raise HTTPException(404, "Bill not found")

    if bill.status == "PAID":
        return {"message": "Bill already paid"}

    bill.status = "PAID"
    bill.save()

    return {
        "message": "Bill marked as PAID",
        "bill_id": str(bill.id),
        "amount": bill.grand_total,
        "payment_mode": payment_mode,
        "paid_at": datetime.utcnow()
    }


# =====================================================
# DELETE ALL BILLS
# =====================================================
@router.delete("/admin/billing/delete-all")
def delete_all_bills():
    bills = PatientBill.objects()
    count = bills.count()
    bills.delete()

    return {
        "message": "All bills deleted successfully",
        "deleted_count": count
    }
