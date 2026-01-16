# from fastapi import APIRouter, Depends, HTTPException
# from core.dependencies import admin_required, get_current_user
# from models import *

# from reportlab.pdfgen import canvas
# import os
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib import colors
# from reportlab.lib.units import inch
# from reportlab.lib.enums import TA_CENTER




# # def generate_bill_pdf(bill):
# #     os.makedirs("media/bills", exist_ok=True)
# #     path = f"media/bills/bill_{bill.id}.pdf"

# #     c = canvas.Canvas(path, pagesize=A4)
# #     w, h = A4
# #     y = h - 40

# #     c.setFont("Helvetica-Bold", 14)
# #     c.drawString(40, y, "PATIENT BILL INVOICE")

# #     y -= 30
# #     c.setFont("Helvetica", 10)
# #     c.drawString(40, y, f"Patient: {bill.patient.user.name}")
# #     c.drawString(350, y, f"Date: {bill.bill_date.strftime('%d-%m-%Y')}")

# #     y -= 30
# #     c.setFont("Helvetica-Bold", 11)
# #     c.drawString(40, y, "Billing Items")
# #     y -= 20

# #     c.setFont("Helvetica", 10)
# #     for i in bill.items:
# #         c.drawString(40, y, i.title)
# #         c.drawRightString(550, y, f"₹ {i.total_price}")
# #         y -= 16

# #     y -= 15
# #     c.drawString(40, y, f"Sub Total: ₹ {bill.sub_total}")
# #     y -= 15
# #     c.drawString(40, y, f"Discount: ₹ {bill.discount}")
# #     y -= 15
# #     c.drawString(40, y, f"Extra Charges: ₹ {bill.extra_charges}")

# #     y -= 20
# #     c.setFont("Helvetica-Bold", 11)
# #     c.drawString(40, y, f"TOTAL PAYABLE: ₹ {bill.grand_total}")

# #     c.save()
# #     return path
# def generate_bill_pdf(bill):
#     os.makedirs("media/bills", exist_ok=True)
#     path = f"media/bills/bill_{bill.id}.pdf"

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

#     # ================= HEADER =================
#     header_style = ParagraphStyle(
#         "Header",
#         parent=styles["Title"],
#         alignment=TA_CENTER
#     )

#     elements.append(Paragraph(
#         "WeCare Home Healthcare Services",
#         header_style
#     ))

#     elements.append(Paragraph(
#         "Phone: +91 8432144275 &nbsp;&nbsp; | &nbsp;&nbsp; "
#         "Email: wcare823@gmail.com<br/><br/>",
#         styles["Normal"]
#     ))

#     # ================= PATIENT INFO =================
#     elements.append(Paragraph(
#         f"<b>Patient Name:</b> {bill.patient.user.name}<br/>"
#         f"<b>Date:</b> {bill.created_at.strftime('%d-%m-%Y')}<br/>"
#         f"<b>Bill Type:</b> {bill.bill_type}<br/><br/>",
#         styles["Normal"]
#     ))

#     # ================= MEDICINE TABLE =================
#     table_data = [
#         ["Sr No", "Medicine / Item", "Dosage", "Timing", "Amount (₹)"]
#     ]

#     sr = 1
#     for item in bill.items:
#         table_data.append([
#             sr,
#             item.title.replace("Medicine: ", ""),
#             getattr(item, "dosage", "-"),
#             getattr(item, "timing", "-"),
#             f"{item.total_price:.2f}"
#         ])
#         sr += 1

#     table = Table(
#         table_data,
#         colWidths=[
#             0.7 * inch,
#             3.2 * inch,
#             1.2 * inch,
#             1.3 * inch,
#             1.3 * inch
#         ]
#     )

#     table.setStyle(TableStyle([
#         ("GRID", (0, 0), (-1, -1), 1, colors.black),
#         ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
#         ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
#         ("ALIGN", (0, 0), (-1, 0), "CENTER"),
#         ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
#         ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
#         ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
#         ("TOPPADDING", (0, 0), (-1, -1), 8),
#     ]))

#     elements.append(table)

#     # ================= TOTAL SECTION =================
#     elements.append(Paragraph("<br/>", styles["Normal"]))

#     totals_style = ParagraphStyle(
#         "Totals",
#         parent=styles["Normal"],
#         leftIndent=300
#     )

#     elements.append(Paragraph(
#         f"Sub Total : ₹ {bill.sub_total:.2f}<br/>"
#         f"Discount : ₹ {bill.discount:.2f}<br/>"
#         f"Extra Charges : ₹ {bill.extra_charges:.2f}<br/>",
#         totals_style
#     ))

#     # ================= GST SECTION =================
#     if bill.bill_type == "GST" and bill.gst_amount > 0:
#         cgst = bill.gst_amount / 2
#         sgst = bill.gst_amount / 2

#         elements.append(Paragraph(
#             f"CGST ({bill.gst_percent/2:.0f}%) : ₹ {cgst:.2f}<br/>"
#             f"SGST ({bill.gst_percent/2:.0f}%) : ₹ {sgst:.2f}<br/>",
#             totals_style
#         ))

#     # ================= GRAND TOTAL =================
#     elements.append(Paragraph(
#         f"<b>Total Payable : ₹ {bill.grand_total:.2f}</b>",
#         totals_style
#     ))

#     # ================= FOOTER =================
#     elements.append(Paragraph("<br/><br/>", styles["Normal"]))
#     elements.append(Paragraph(
#         "This is a computer generated bill.<br/>"
#         "Thank you for choosing WeCare Home Healthcare Services.",
#         styles["Italic"]
#     ))

#     doc.build(elements)
#     return path



# router = APIRouter(prefix="/billing", tags=["Billing 2"])


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
#             # items.append(
#             #     BillItem(
#             #         title=f"Medicine: {m.medicine_name}",
#             #         quantity=1,
#             #         unit_price=m.price,
#             #         total_price=m.price
#             #     )
#             # )
#             items.append(
#                 BillItem(
#                     title=f"Medicine: {m.medicine_name}",
#                     quantity=1,
#                     unit_price=m.price,
#                     total_price=m.price,
#                     dosage=m.dosage,
#                     timing=m.timing
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

#     # bill = PatientBill(
#     #     patient=patient,
#     #     items=items,
#     #     sub_total=sub_total,
#     #     discount=discount,
#     #     extra_charges=extra,
#     #     grand_total=grand_total,
#     #     bill_month=datetime.utcnow().strftime("%Y-%m"),
#     #     created_by=admin
#     # )
#     # bill.save()
#     bill = PatientBill(
#     patient=patient,
#     items=items,
#     sub_total=sub_total,
#     discount=discount,
#     extra_charges=extra,
#     gst_percent=gst_percent if gst_enabled else 0,
#     gst_amount=gst_amount,
#     grand_total=grand_total,
#     bill_type=bill_type,
#     bill_month=datetime.utcnow().strftime("%Y-%m"),
#     created_by=admin
# )
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
# def delete_all_bills(admin=Depends(admin_required)):
#     bills = PatientBill.objects()

#     count = bills.count()
#     bills.delete()

#     return {
#         "message": "All bills deleted successfully",
#         "deleted_count": count
#     }
