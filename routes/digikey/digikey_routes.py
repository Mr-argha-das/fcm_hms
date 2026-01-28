from core.services.digikey_service import get_access_token, product_details, search_products
from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/digikey", tags=["DigiKey"])


# 🔹 Get token (testing only)
@router.get("/token")
async def token():
    try:
        t = await get_access_token()
        return {"access_token": t}
    except Exception as e:
        raise HTTPException(500, str(e))


# 🔹 Search products
@router.get("/search")
async def search(q: str, limit: int = 5):
    try:
        data = await search_products(q, limit)
        return data
    except Exception as e:
        raise HTTPException(500, str(e))


# 🔹 Product details
@router.get("/details/{part_number}")
async def details(part_number: str):
    try:
        data = await product_details(part_number)
        return data
    except Exception as e:
        raise HTTPException(500, str(e))
