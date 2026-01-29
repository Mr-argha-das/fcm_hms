from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from .schemas import (
    SendOTPRequest, VerifyOTPRequest,
    PasswordLoginRequest
)
from fastapi.responses import JSONResponse
import requests
from pydantic import BaseModel
from models import User
from core.security import create_access_token, verify_password
from core.dependencies import get_current_user, admin_required




class TokenResponse(BaseModel):
    access_token: str
    role: str
    token_type: str = "bearer"


API_KEY = "dfd091ab0abebbbe28c5fb4bcc3bd8d9"
BASE_URL = "https://connect.muzztech.com/api/V1"

router = APIRouter(prefix="/auth", tags=["Auth"])

STATIC_OTP = "123456"

# @router.post("/send-otp")
# def send_otp(data: SendOTPRequest):
#     # Dev / Testing OTP
#     return {
#         "message": f"OTP sent to {data.phone}",
#         "otp": STATIC_OTP  # remove in production
#     }

@router.post("/send-otp")
def send_otp(data: SendOTPRequest):

    params = {
        "api_key": API_KEY,
        "otp_template_name": "OTP",
        "phone_number": data.phone
    }

    try:
        res = requests.get(BASE_URL, params=params, timeout=10)
        response = res.json()
    except:
        raise HTTPException(500, "OTP service unreachable")

    if res.status_code != 200:
        raise HTTPException(400, "Failed to send OTP")

    otp_session = response.get("Details")

    if not otp_session:
        raise HTTPException(400, "OTP session not received")

    # ✅ create user if not exists
    user = User.objects(phone=data.phone).first()

    if not user:
        user = User(phone=data.phone, role="PATIENT")

    user.otp_session = otp_session
    user.otp_verified = False
    user.save()

    return {"message": "OTP sent successfully"}


@router.post("/verify-otp")
def verify_otp(data: VerifyOTPRequest):

    # 🔹 find user
    user = User.objects(phone=data.phone).first()

    if not user:
        raise HTTPException(404, "User not found")

    if not user.otp_session:
        raise HTTPException(400, "OTP session missing. Please resend OTP")


    params = {
        "api_key": API_KEY,
        "otp_session": user.otp_session,   # from Details
        "otp_entered_by_user": data.otp
    }

    try:
        res = requests.get(BASE_URL, params=params, timeout=10)
        response = res.json()
    except Exception:
        raise HTTPException(500, "OTP service unreachable")


    # 🔹 provider validation
    if res.status_code != 200:
        raise HTTPException(400, "OTP verification failed")

    status_value = response.get("Status", "").lower()

    if status_value != "success":
        raise HTTPException(400, response.get("Details", "Invalid OTP"))


    # 🔹 success login flow
    if not user.is_active:
        raise HTTPException(403, "User blocked")


    user.otp_verified = True
    user.otp_session = None
    user.last_login = datetime.utcnow()

# 🔥 SINGLE SESSION LOGIC
    user.token_version += 1   # old tokens invalid
    user.save()

    token = create_access_token(
    {
        "user_id": str(user.id),
        "role": user.role
    },
    user.token_version
    )



    return {
        "access_token": token,
        "role": user.role,
        "token_type": "bearer"
    }

# @router.post("/verify-otp")
# def verify_otp(data: VerifyOTPRequest):

#     user = User.objects(phone=data.phone).first()

#     if not user or not user.otp_session:
#         raise HTTPException(400, "OTP session missing")

#     params = {
#         "api_key": API_KEY,
#         "otp_session": user.otp_session,
#         "otp_entered_by_user": data.otp
#     }

#     try:
#         res = requests.get(BASE_URL, params=params, timeout=10)
#         response = res.json()
#     except:
#         raise HTTPException(500, "OTP service unreachable")

#     # ✅ FIX HERE
#     if res.status_code != 200 or response.get("Status") != "Success":
#         raise HTTPException(400, "Invalid OTP")

#     # ✅ success
#     user.otp_verified = True
#     user.otp_session = None
#     user.last_login = datetime.utcnow()

#     if not user.is_active:
#         raise HTTPException(403, "User blocked")

#     user.save()

#     token = create_access_token({
#         "user_id": str(user.id),
#         "role": user.role
#     })

#     return {
#         "access_token": token,
#         "role": user.role
#     }

# @router.post("/verify-otp",)
# def verify_otp(data: VerifyOTPRequest):
#     if data.otp != STATIC_OTP:
#         raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OTP")

#     user = User.objects(phone=data.phone).first()
#     if not user:
#         # Create new user
#        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
#     else:
#         user.otp_verified = True
#         if not user.is_active:
#             raise HTTPException(status.HTTP_403_FORBIDDEN, "User blocked")
        

  
#     # user.role = data.role
#     user.last_login = datetime.utcnow()
#     user.save()

#     token = create_access_token({
#         "user_id": str(user.id),
#         "role": user.role
#     })

#     return {"access_token": token, "role": user.role}



@router.post("/login-password", response_model=TokenResponse)
def login_password(data: PasswordLoginRequest):
    user = User.objects(phone=data.phone).first()

    if not user or not user.password_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User blocked")

    user.last_login = datetime.utcnow()
    user.save()

    token = create_access_token({
        "user_id": str(user.id),
        "role": user.role
    })

    response = JSONResponse({
        "access_token": token,
        "role": user.role
    })

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax"
    )

    return response

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "phone": user.phone,
        "role": user.role,
        "active": user.is_active,
        "last_login": user.last_login
    }

@router.post("/logout")
def logout():
    return {"message": "Logout successful (client-side token delete)"}

@router.post("/admin/block-user")
def block_user(user_id: str, admin: User = Depends(admin_required)):
    user = User.objects(id=user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = False
    user.save()
    return {"message": "User blocked successfully"}


@router.post("/admin/unblock-user")
def unblock_user(user_id: str, admin: User = Depends(admin_required)):
    user = User.objects(id=user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = True
    user.save()
    return {"message": "User unblocked successfully"}
