from fastapi import APIRouter, Depends, HTTPException
from core.dependencies import admin_required, get_current_user
from models import *
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os



def generate_bill_pdf(bill):
    os.makedirs("media/bills", exist_ok=True)
    path = f"media/bills/bill_{bill.id}.pdf"

    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = h - 40

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "PATIENT BILL INVOICE")

    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Patient: {bill.patient.user.name}")
    c.drawString(350, y, f"Date: {bill.bill_date.strftime('%d-%m-%Y')}")

    y -= 30
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Billing Items")
    y -= 20

    c.setFont("Helvetica", 10)
    for i in bill.items:
        c.drawString(40, y, i.title)
        c.drawRightString(550, y, f"₹ {i.total_price}")
        y -= 16

    y -= 15
    c.drawString(40, y, f"Sub Total: ₹ {bill.sub_total}")
    y -= 15
    c.drawString(40, y, f"Discount: ₹ {bill.discount}")
    y -= 15
    c.drawString(40, y, f"Extra Charges: ₹ {bill.extra_charges}")

    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, f"TOTAL PAYABLE: ₹ {bill.grand_total}")

    c.save()
    return path
router = APIRouter(prefix="/billing", tags=["Billing"])
@router.post("/admin/invoice/create")
def create_invoice(
    patient_id: str,
    amount: float,
    admin=Depends(admin_required)
):
    patient = PatientProfile.objects(id=patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    invoice = PatientInvoice(
        patient=patient,
        total_amount=amount,
        paid_amount=0,
        due_amount=amount,
        status="DUE"
    ).save()

    return {"message": "Invoice created", "invoice_id": str(invoice.id)}
@router.get("/patient/my")
def my_invoices(user=Depends(get_current_user)):
    patient = PatientProfile.objects(user=user).first()
    return PatientInvoice.objects(patient=patient)
@router.get("/patient/{invoice_id}")
def view_invoice(invoice_id: str, user=Depends(get_current_user)):
    patient = PatientProfile.objects(user=user).first()
    invoice = PatientInvoice.objects(id=invoice_id, patient=patient).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    return invoice
@router.post("/admin/mark-paid")
def mark_paid(invoice_id: str, admin=Depends(admin_required)):
    invoice = PatientInvoice.objects(id=invoice_id).first()
    invoice.paid_amount = invoice.total_amount
    invoice.due_amount = 0
    invoice.status = "PAID"
    invoice.save()
    return {"message": "Invoice marked PAID"}
@router.post("/admin/mark-partial")
def mark_partial(
    invoice_id: str,
    amount_paid: float,
    admin=Depends(admin_required)
):
    invoice = PatientInvoice.objects(id=invoice_id).first()

    invoice.paid_amount += amount_paid
    invoice.due_amount = invoice.total_amount - invoice.paid_amount

    invoice.status = "PAID" if invoice.due_amount <= 0 else "PARTIAL"
    invoice.save()

    return {"message": "Partial payment updated"}




@router.post("/admin/billing/generate")
def generate_bill(
    payload: dict,
    admin=Depends(admin_required)
):  
    
# Example payload:
#     {
#   "patient_id": "PATIENT_ID",
#   "discount": 100,
#   "extra_charges": 50,
#   "other_items": [
#     {
#       "title": "Emergency Service",
#       "quantity": 1,
#       "unit_price": 1000
#     }
#   ]
# }

    patient = PatientProfile.objects(id=payload["patient_id"]).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    items = []
    medicine_list = []

    # 🔹 MEDICINES FROM PatientMedication
    meds = PatientMedication.objects(patient=patient)
    for m in meds:
        if m.price:
            items.append(
                BillItem(
                    title=f"Medicine: {m.medicine_name}",
                    quantity=1,
                    unit_price=m.price,
                    total_price=m.price
                )
            )
            medicine_list.append({
                "name": m.medicine_name,
                "dosage": m.dosage,
                "price": m.price
            })

    # 🔹 OTHER BILLING ITEMS
    for oi in payload.get("other_items", []):
        total = oi["quantity"] * oi["unit_price"]
        items.append(
            BillItem(
                title=oi["title"],
                quantity=oi["quantity"],
                unit_price=oi["unit_price"],
                total_price=total
            )
        )

    # 🔢 CALCULATION
    sub_total = sum(i.total_price for i in items)
    discount = payload.get("discount", 0)
    extra = payload.get("extra_charges", 0)

    grand_total = max(sub_total - discount + extra, 0)

    bill = PatientBill(
        patient=patient,
        items=items,
        sub_total=sub_total,
        discount=discount,
        extra_charges=extra,
        grand_total=grand_total,
        bill_month=datetime.utcnow().strftime("%Y-%m"),
        created_by=admin
    )
    bill.save()

    pdf_path = generate_bill_pdf(bill)
    bill.pdf_file = pdf_path
    bill.save()

    return {
        "message": "Bill generated successfully",
        "bill_id": str(bill.id),
        "patient": patient.user.name,
        "medicines": medicine_list,
        "sub_total": sub_total,
        "grand_total": grand_total,
        "pdf": pdf_path
    }


@router.get("/admin/patient/{patient_id}/bills")
def get_patient_bills(patient_id: str, admin=Depends(admin_required)):
    bills = PatientBill.objects(patient=patient_id).order_by("-bill_date")

    return [
        {
            "bill_id": str(b.id),
            "date": b.bill_date,
            "amount": b.grand_total,
            "pdf": b.pdf_file,
            "status": b.status
        }
        for b in bills
    ]


@router.post("/admin/billing/mark-paid")
def mark_bill_paid(
    bill_id: str,
    payment_mode: str = "CASH",   # CASH / UPI / BANK
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