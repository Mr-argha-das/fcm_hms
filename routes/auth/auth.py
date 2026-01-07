from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from .schemas import (
    SendOTPRequest, VerifyOTPRequest,
    PasswordLoginRequest, TokenResponse
)
from models import User
from core.security import create_access_token, verify_password
from core.dependencies import get_current_user, admin_required

router = APIRouter(prefix="/auth", tags=["Auth"])

STATIC_OTP = "123456"

@router.post("/send-otp")
def send_otp(data: SendOTPRequest):
    # Dev / Testing OTP
    return {
        "message": f"OTP sent to {data.phone}",
        "otp": STATIC_OTP  # remove in production
    }
@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(data: VerifyOTPRequest):
    if data.otp != STATIC_OTP:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OTP")

    user = User.objects(phone=data.phone).first()
    if not user:
        # Create new user
       raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    else:
        user.otp_verified = True
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "User blocked")
        

  
    # user.role = data.role
    user.last_login = datetime.utcnow()
    user.save()

    token = create_access_token({
        "user_id": str(user.id),
        "role": user.role
    })

    return {"access_token": token}
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

    return {"access_token": token}
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
