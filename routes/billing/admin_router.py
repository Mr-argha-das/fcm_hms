from fastapi import APIRouter, Depends, HTTPException
from core.dependencies import admin_required, get_current_user
from models import PatientInvoice, PatientProfile

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
