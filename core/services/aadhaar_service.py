import asyncio
from models import NurseProfile


async def verify_aadhaar_async(nurse_id: str):
    """
    Background verification simulation.
    Later you can replace with real KYC API.
    """

    await asyncio.sleep(5)  # simulate processing

    nurse = NurseProfile.objects(id=nurse_id).first()
    if not nurse:
        return

    # 🔥 Example logic (dummy)
    # Later call real OCR/API here

    nurse.aadhaar_verified = True
    nurse.aadhaar_verification_status = "VERIFIED"
    nurse.save()
