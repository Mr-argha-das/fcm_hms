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
from models import BillItem, PatientMedication, PatientProfile, PatientBill
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


def generate_bill_pdf(bill, gst_percent: float = 0):
    media_bills_dir = os.path.join(BASE_DIR, "media", "bills")
    os.makedirs(media_bills_dir, exist_ok=True)

    suffix = "gst" if gst_percent > 0 else "nogst"
    path = os.path.join(
        media_bills_dir,
        f"bill_{bill.id}_{suffix}.pdf"
    )

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elements = []

    # ================= DATE =================
    bill_date = getattr(bill, "created_at", None)
    date_str = bill_date.strftime("%d-%m-%Y") if bill_date else "-"

    # ================= HEADER IMAGE =================
    logo_path = os.path.join(BASE_DIR, "media", "logos", "wecare_header.png")
    if os.path.exists(logo_path):
        header_img = Image(logo_path, width=3.9 * inch, height=1.4 * inch)
        header_img.hAlign = "CENTER"
        elements.append(header_img)
#     os.makedirs("media/bills", exist_ok=True)
# # changes
#     suffix = "gst" if gst_percent > 0 else "nogst"
#     path = f"media/bills/bill_{bill.id}_{suffix}.pdf"

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
#     logo_path = "media/logos/wecare_header.png"
#     if os.path.exists(logo_path):
#         header_img = Image(logo_path, width=3.9 * inch, height=1.4 * inch)
#         header_img.hAlign = "CENTER"
#         elements.append(header_img)

    elements.append(Paragraph("<br/>", styles["Normal"]))

    # ================= CONTACT ROW =================
    contact_row = Table(
        [[
            
            "+91 8432144275",
            "wcare823@gmail.com",
            "www.wecarehcs.com"
        ]],
        colWidths=[2.3 * inch, 2.3 * inch, 2.4 * inch]
    )

    contact_row.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))

    elements.append(contact_row)
    elements.append(Paragraph("<br/>", styles["Normal"]))

    # ================= PATIENT NAME / DATE =================
    patient_row = Table(
        [[
            f"Patient Name :  {bill.patient.user.name}",
            f"Date :  {date_str}"
        ]],
        colWidths=[5 * inch, 2 * inch]
    )

    patient_row.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(patient_row)
    elements.append(Paragraph("<br/>", styles["Normal"]))

    # ================= ITEMS TABLE =================
    table_data = [["#", "Item", "Qty", "Amount (Rs)"]]

    # for idx, item in enumerate(bill.items, 1):
    #     table_data.append([
    #         idx,
    #         item["title"],
    #         item["quantity"],
    #         # f"{item['unit_price']:.2f}",
    #         f"{item.total_price:.2f}",
    #     ])

    for idx, item in enumerate(bill.items, 1):
      table_data.append([
        idx,
        item.title,
        item.quantity,
        f"{item.total_price:.2f}",
    ])

    items_table = Table(
        table_data,
        colWidths=[0.5 * inch, 4.7 * inch, 0.6  * inch, 1.2 * inch]
    )

    items_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elements.append(items_table)
    elements.append(Paragraph("<br/>", styles["Normal"]))

    # ================= TOTALS =================
    gst_amount = round((bill.grand_total * gst_percent) / 100, 2)
    total_with_gst = bill.grand_total + gst_amount

    totals_data = [
        ["", "", "Sub Total :", f"{bill.sub_total:.2f} Rs"],
        ["", "", "Discount :", f"{bill.discount:.2f} Rs"],
        ["", "", "Extra Charges :", f"{bill.extra_charges:.2f} Rs"],
        ["", "", "Total (Without GST) :", f"{bill.grand_total:.2f} Rs"],
    ]

    if gst_percent > 0:
        totals_data.append(
            ["", "", f"GST @ {gst_percent}% :", f"{gst_amount:.2f} Rs"]
        )
        totals_data.append(
            ["", "", "Total Payable :", f"{total_with_gst:.2f} Rs"]
        )
    
    totals_table = Table(
        totals_data,
        colWidths=[0.6 * inch, 3 * inch, 1.2 * inch, 2.2 * inch]
    )
    
    totals_table.setStyle(TableStyle([
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("FONT", (2, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(totals_table) 
    
    # ================= FOOTER =================
    elements.append(Paragraph("<br/><br/>", styles["Normal"]))
    elements.append(Paragraph(
        "This is a computer generated bill.",
         ParagraphStyle("footer", alignment=TA_CENTER, fontSize=9)
    ))
    
    doc.build(elements)
    return path

# =====================================================
# GENERATE BILL
# =====================================================
@router.post("/admin/billing/generate")
async def generate_bill(
    request: Request,
    user=Depends(get_current_user)
):
    data = await request.json()

    patient = PatientProfile.objects.get(id=data["patient_id"])

    items = []
    sub_total = 0
    # ================= MEDICINES =================
    medicines = PatientMedication.objects(patient=patient)

    for m in medicines:
     if m.price:
        items.append(
            BillItem(
                title=f"Medicine: {m.medicine_name}",
                quantity=1,
                unit_price=m.price,
                total_price=m.price,
                dosage=m.dosage
            )
        )
        sub_total += m.price


    for i in data.get("other_items", []):
        total = i["quantity"] * i["unit_price"]
        items.append(
         BillItem(
          title=i["title"],
          quantity=i["quantity"],
          unit_price=i["unit_price"],
          total_price=total
        )
)
        sub_total += total

    discount = data.get("discount", 0)
    extra = data.get("extra_charges", 0)
    grand_total = sub_total - discount + extra

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
        "bill_id": str(bill.id)
    }


# =====================================================
# DOWNLOAD BILL (GST / NON-GST)
# =====================================================

# @router.get("/admin/billing/{bill_id}/download", response_model=None)
# def download_bill_pdf(
#     bill_id: str,
#     gst_percent: float = Query(0, ge=0, le=100),
#     request: Request = None
# ):
#     bill = PatientBill.objects(id=bill_id).first()
#     if not bill:
#         raise HTTPException(status_code=404, detail="Bill not found")

#     base_dir = request.app.state.BASE_DIR

#     pdf_path = generate_bill_pdf(
#         bill=bill,
#         gst_percent=gst_percent,
#         base_dir=base_dir
#     )

#     if not os.path.exists(pdf_path):
#         raise HTTPException(
#             status_code=500,
#             detail=f"PDF not found at {pdf_path}"
#         )

#     filename = (
#         f"Bill_{bill_id}_GST_{gst_percent}.pdf"
#         if gst_percent > 0
#         else f"Bill_{bill_id}_No_GST.pdf"
#     )

#     return FileResponse(
#         pdf_path,
#         media_type="application/pdf",
#         filename=filename
#     )

# @router.get("/admin/billing/{bill_id}/download", response_model=None)
# def download_bill_pdf(
#     bill_id: str,
#     gst_percent: float = Query(0, ge=0, le=100),
# ):
#     bill = PatientBill.objects(id=bill_id).first()
#     if not bill:
#         raise HTTPException(status_code=404, detail="Bill not found")

#     pdf_path = generate_bill_pdf(
#         bill=bill,
#         gst_percent=gst_percent
#     )

#     if not os.path.exists(pdf_path):
#         raise HTTPException(
#             status_code=500,
#             detail=f"PDF not found at {pdf_path}"
#         )

#     filename = (
#         f"Bill_{bill_id}_GST_{gst_percent}.pdf"
#         if gst_percent > 0
#         else f"Bill_{bill_id}_No_GST.pdf"
#     )

#     return FileResponse(
#         pdf_path,
#         media_type="application/pdf",
#         filename=filename
#     )

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
