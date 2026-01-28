import os
import base64
import httpx
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

CLIENT_ID = os.getenv("DIGIKEY_CLIENT_ID")
CLIENT_SECRET = os.getenv("DIGIKEY_CLIENT_SECRET")

TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
BASE_URL = "https://sandbox-api.digikey.com"


# 🔥 simple token cache (avoid calling token API again & again)
_cached_token = None
_token_expiry = None


async def get_access_token():
    global _cached_token, _token_expiry

    # return cached if valid
    if _cached_token and _token_expiry and datetime.utcnow() < _token_expiry:
        return _cached_token

    creds = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded = base64.b64encode(creds.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "client_credentials"
    }

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(TOKEN_URL, headers=headers, data=data)

    if res.status_code != 200:
        raise Exception("Failed to get DigiKey token")

    response = res.json()

    _cached_token = response["access_token"]
    expires_in = response.get("expires_in", 1800)

    _token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)

    return _cached_token


# 🔥 Product Search
async def search_products(keyword: str, limit: int = 5):
    token = await get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "X-DIGIKEY-Client-Id": CLIENT_ID,
        "Accept": "application/json"
    }

    url = f"{BASE_URL}/products/v4/search/keyword"

    params = {
        "keywords": keyword,
        "limit": limit
    }

    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.get(url, headers=headers, params=params)

    return res.json()


# 🔥 Product Details
async def product_details(part_number: str):
    token = await get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "X-DIGIKEY-Client-Id": CLIENT_ID,
        "Accept": "application/json"
    }

    url = f"{BASE_URL}/products/v4/partnumber/{part_number}"

    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.get(url, headers=headers)

    return res.json()
