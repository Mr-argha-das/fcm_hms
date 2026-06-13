from fastapi import APIRouter, HTTPException
from datetime import datetime
from pydantic import BaseModel

from models import AboutUs


router = APIRouter(prefix="/admin", tags=["About Us"])


# ===============================
# ✅ SCHEMA
# ===============================
class AboutUsUpdateSchema(BaseModel):
    name: str
    designation: str
    description: str
    profile_image: str


# ===============================
# 🔹 PUBLIC GET (APP use karega)
# ===============================
@router.get("/about-us-get")
def get_about_us():
    about = AboutUs.objects.first()
    # 🔥 if no data → return default empty
    if not about:
        return {
            "id": None,
            "name": "",
            "designation": "",
            "description": "",
            "profile_image": "",
        }

    return {
        "id": str(about.id),
        "name": about.name,
        "designation": about.designation,
        "description": about.description,
        "profile_image": about.profile_image,
    }


# ===============================
# 🔹 ADMIN UPDATE
# ===============================
@router.put("/get-update")
def update_about_us(body: AboutUsUpdateSchema):
    try:
        about = AboutUs.objects.first()

        # 🔥 auto create first time
        if not about:
            about = AboutUs()

        about.name = body.name
        about.designation = body.designation
        about.description = body.description
        about.profile_image = body.profile_image
        about.updated_at = datetime.utcnow()

        about.save()

        return {
            "success": True,
            "message": "About Us updated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
