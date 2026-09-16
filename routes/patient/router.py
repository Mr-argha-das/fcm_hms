@equipment_router.get("/request-equipment/all")
def get_all_requests():

    requests = UserEquipmentRequest.objects()

    data = []

    for r in requests:
        patient_id = ""
        patient_name = ""
        patient_phone = ""
        ward = ""
        try:
            if r.patient:
                patient_id = str(r.patient.id)
                if getattr(r.patient, "user", None):
                    patient_name = getattr(r.patient.user, "name", "") or ""
                    patient_phone = getattr(r.patient.user, "phone", "") or ""
                ward = str(getattr(r.patient, "address", "") or "")
        except Exception:
            pass

        equip_id = ""
        equip_title = ""
        equip_image = ""
        equip_price = 0
        try:
            if r.equipment:
                equip_id = str(r.equipment.id)
                equip_title = getattr(r.equipment, "title", "") or ""
                equip_image = getattr(r.equipment, "image", "") or ""
                equip_price = getattr(r.equipment, "price", 0) or 0
        except Exception:
            pass

        data.append({
            "id": str(r.id),
            "patient_id": patient_id,
            "patient_name": patient_name or "Unknown Patient",
            "patient_phone": patient_phone or "-",
            "equipment_phone": patient_phone or "-",
            "ward": ward or "-",
            "equipment_id": equip_id,
            "equipment_title": equip_title or "Unknown Equipment",
            "equipment_image": equip_image or "",
            "equipment_price": equip_price or 0,
            "request_time": r.created_at.strftime("%Y-%m-%d %H:%M") if getattr(r, "created_at", None) else "",
            "status": bool(r.status)
        })

    return data

@equipment_router.get("/request-equipment/patient/{patient_id}")
def get_patient_requests(patient_id: str):

    requests = UserEquipmentRequest.objects(patient=patient_id)

    data = []

    for r in requests:
        equip_title = "Unknown Equipment"
        equip_image = ""
        try:
            if r.equipment:
                equip_title = getattr(r.equipment, "title", "") or "Unknown Equipment"
                equip_image = getattr(r.equipment, "image", "") or ""
        except Exception:
            pass

        data.append({
            "id": str(r.id),
            "equipment_title": equip_title,
            "equipment_image": equip_image,
            "status": bool(r.status)
        })

    return data