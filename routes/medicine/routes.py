from fastapi import APIRouter, Depends, Form, HTTPException
from datetime import datetime

from fastapi.responses import RedirectResponse
from core.dependencies import admin_required, get_current_user
from models import Medicine
router = APIRouter(prefix="/md", tags=["medicine"])
@router.post("/admin/medicine/create")
def create_medicine(
    payload: dict,
    admin=Depends(admin_required)
): 
    # Example payload:
#     {
#   "name": "Paracetamol",
#   "company_name": "Cipla",
#   "dosage": "500mg",
#   "dosage_form": "Tablet",
#   "price": 120
# }


    if Medicine.objects(name=payload.get("name")).first():
        raise HTTPException(status_code=400, detail="Medicine already exists")

    med = Medicine(**payload)
    med.save()
    return {"message": "Medicine created"}



@router.get("/admin/medicine")
def get_all_medicines():
    meds = Medicine.objects(is_active=True)

    return [
        {
            "id": str(m.id),
            "name": m.name,
            "company": m.company_name,
            "dosage": m.dosage,
            "form": m.dosage_form,
            "price": m.price
        }
        for m in meds
    ]

@router.delete("/admin/medicine/{medicine_id}")
def delete_medicine(
    medicine_id: str,
    admin=Depends(admin_required)
):
    med = Medicine.objects(id=medicine_id).first()

    if not med:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    med.delete()   # ✅ permanent delete from MongoDB

    return {
        "message": "Medicine deleted permanently",
        "id": medicine_id
    }




@router.put("/admin/medicine/{medicine_id}")
def update_medicine(
    medicine_id: str,
    payload: dict,
    admin=Depends(admin_required)
):
    med = Medicine.objects(id=medicine_id).first()
    if not med:
        raise HTTPException(404, "Medicine not found")

    for k, v in payload.items():
        setattr(med, k, v)

    med.save()
    return {"message": "Medicine updated"}