from fastapi import APIRouter, HTTPException
from typing import List

from models import HospitalModel
from routes.auth.schemas import HospitalCreate, HospitalResponse


router = APIRouter(prefix="/hospital", tags=["Hospital"])

@router.post("/create", response_model=HospitalResponse)
def create_hospital(payload: HospitalCreate):
    hospital = HospitalModel(**payload.dict()).save()

    return {
        "id": str(hospital.id),
        **payload.dict()
    }

@router.get("/get-all", response_model=List[HospitalResponse])
def get_hospitals():
    hospitals = HospitalModel.objects()

    return [
        {
            "id": str(h.id),
            "name": h.name,
            "aname": h.aname,
            "acontact": h.acontact,
            "address": h.address,
            "branch": h.branch
        }
        for h in hospitals
    ]


@router.get("/get/{hospital_id}", response_model=HospitalResponse)
def get_single_hospital(hospital_id: str):
    hospital = HospitalModel.objects(id=hospital_id).first()

    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    return {
        "id": str(hospital.id),
        "name": hospital.name,
        "aname": hospital.aname,
        "acontact": hospital.acontact,
        "address": hospital.address,
        "branch": hospital.branch
    }


@router.put("/update/{hospital_id}", response_model=HospitalResponse)
def update_hospital(hospital_id: str, payload: HospitalCreate):
    hospital = HospitalModel.objects(id=hospital_id).first()

    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    hospital.name = payload.name
    hospital.aname = payload.aname
    hospital.acontact = payload.acontact
    hospital.address = payload.address
    hospital.branch = payload.branch
    hospital.save()

    return {
        "id": str(hospital.id),
        "name": hospital.name,
        "aname": hospital.aname,
        "acontact": hospital.acontact,
        "address": hospital.address,
        "branch": hospital.branch
    }