from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from .schemas import (
    SendOTPRequest, VerifyOTPRequest,
    PasswordLoginRequest
)

from fastapi.responses import JSONResponse
import requests
from pydantic import BaseModel, Field

from models import PatientProfile, User
from core.security import create_access_token, verify_password
from core.dependencies import get_current_user, admin_required
from core.permissions import first_allowed_admin_path
from core.test_accounts import TEST_ACCOUNTS, TEST_OTP, is_test_account




class TokenResponse(BaseModel):
    access_token: str
    role: str
    token_type: str = "bearer"


API_KEY = "dfd091ab0abebbbe28c5fb4bcc3bd8d9"
BASE_URL = "https://connect.muzztech.com/api/V1"

router = APIRouter(prefix="/auth", tags=["Auth"])

LEGACY_TEST_PHONE = "8104144303"


def ensure_patient_profile(user: User) -> None:
    if user.role == "PATIENT" and not PatientProfile.objects(user=user).first():
        PatientProfile(user=user, created_by="SELF").save()

# @router.post("/send-otp")
# def send_otp(data: SendOTPRequest):
#     # Dev / Testing OTP
#     return {
#         "message": f"OTP sent to {data.phone}",
#         "otp": STATIC_OTP  # remove in production
#     }

def normalize_phone(phone: str):
    return phone.strip().replace("+91", "").replace(" ", "").replace("-", "")

@router.post("/send-otp")
def send_otp(data: SendOTPRequest):
    normalized_phone = normalize_phone(data.phone)

    # 🔥 TEST MODE (Google Reviewer)
    if is_test_account(normalized_phone) or normalized_phone == LEGACY_TEST_PHONE:
        user = User.objects(phone=normalized_phone).first()
        if not user:
            role = TEST_ACCOUNTS.get(normalized_phone, "PATIENT")
            user = User(phone=normalized_phone, role=role).save()
        ensure_patient_profile(user)
        return {
            "message": "Test OTP sent",
            "otp": TEST_OTP
        }

    # 🔹 REAL OTP API CALL
    params = {
        "api_key": API_KEY,
        "otp_template_name": "OTP",
        "phone_number": normalized_phone
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

    # 🔹 Create user if not exists
    user = User.objects(phone=normalized_phone).first()
    if not user:
        user = User(phone=normalized_phone, role="PATIENT")

    user.otp_session = otp_session
    user.otp_verified = False
    user.save()
    ensure_patient_profile(user)

    return {"message": "OTP sent successfully"}

# @router.post("/send-otp")
# def send_otp(data: SendOTPRequest):

#     normalized_phone = normalize_phone(data.phone)

#     if normalized_phone == TEST_PHONE:
#         return {
#             "message": "Test OTP sent",
#             "otp": TEST_OTP
#         }

# @router.post("/verify-otp")
# def verify_otp(data: VerifyOTPRequest):

#     normalized_phone = normalize_phone(data.phone)

#     user = User.objects(phone=data.phone).first()

#     if not user:
#         raise HTTPException(404, "User not found")

#     # ✅ Fixed OTP logic
#     if normalized_phone == TEST_PHONE and data.otp == TEST_OTP:

#         user.otp_verified = True
#         user.otp_session = None
#         user.last_login = datetime.utcnow()
#         user.token_version += 1
#         user.save()

#         token = create_access_token(
#             {
#                 "user_id": str(user.id),
#                 "role": user.role
#             },
#             user.token_version
#         )

#         return {
#             "access_token": token,
#             "role": user.role,
#             "token_type": "bearer"
#         }

@router.post("/verify-otp")
def verify_otp(data: VerifyOTPRequest):
    normalized_phone = normalize_phone(data.phone)

    user = User.objects(phone=normalized_phone).first()

    if not user:
        raise HTTPException(404, "User not found")

    # 🔥 TEST LOGIN (Google Play reviewer)
    if (
        (is_test_account(normalized_phone, user.role) or normalized_phone == LEGACY_TEST_PHONE)
        and data.otp == TEST_OTP
    ):
        user.otp_verified = True
        user.otp_session = None
        user.last_login = datetime.utcnow()
        user.token_version += 1
        user.save()
        ensure_patient_profile(user)

        token = create_access_token(
            {"user_id": str(user.id), "role": user.role},
            user.token_version
        )

        return {
            "access_token": token,
            "user_id": str(user.id),
            "role": user.role,
            "token_type": "bearer"
        }

    # 🔹 Normal OTP Flow
    if not user.otp_session:
        raise HTTPException(400, "OTP session missing. Please resend OTP")

    params = {
        "api_key": API_KEY,
        "otp_session": user.otp_session,
        "otp_entered_by_user": data.otp
    }

    try:
        res = requests.get(BASE_URL, params=params, timeout=10)
        response = res.json()
    except:
        raise HTTPException(500, "OTP service unreachable")

    if res.status_code != 200:
        raise HTTPException(400, "OTP verification failed")

    status_value = response.get("Status", "").lower()

    if status_value != "success":
        raise HTTPException(400, response.get("Details", "Invalid OTP"))

    if not user.is_active:
        raise HTTPException(403, "User blocked")

    # 🔹 Success login
    user.otp_verified = True
    user.otp_session = None
    user.last_login = datetime.utcnow()
    user.token_version += 1
    user.save()
    ensure_patient_profile(user)

    token = create_access_token(
        {"user_id": str(user.id), "role": user.role},
        user.token_version
    )

    return {
        "access_token": token,
        "user_id": str(user.id),
        "role": user.role,
        "token_type": "bearer"
    }




@router.post("/login-password", response_model=TokenResponse)
def login_password(data: PasswordLoginRequest):
    user = User.objects(phone=normalize_phone(data.phone)).first()

    if not user or not user.password_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if data.password != user.password_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    # if not verify_password(data.password, user.password_hash):
    #     raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User blocked")

    user.last_login = datetime.utcnow()
    user.save()

    token = create_access_token(
        {
            "user_id": str(user.id),
            "role": user.role
        },
        user.token_version
    )

    response = JSONResponse({
        "access_token": token,
        "user_id": str(user.id),
        "role": user.role,
        "admin_role_name": user.admin_role_name,
        "redirect_url": first_allowed_admin_path(user) if user.role == "ADMIN" else None
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



class UpdatePasswordRequest(BaseModel):
    phone: str
    password: str   # single field only

@router.post("/update-password")
def update_password(data: UpdatePasswordRequest):

    user = User.objects(phone=normalize_phone(data.phone)).first()

    if not user:
        raise HTTPException(404, "User not found")

    # ✅ direct update (no old password check)
    user.password_hash = data.password

    # logout all sessions
    user.token_version += 1
    user.save()

    return {"message": "Password updated successfully"}
