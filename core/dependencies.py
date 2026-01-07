from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from core.security import SECRET_KEY, ALGORITHM
from models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login-password")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        user = User.objects(id=user_id).first()
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "User blocked by admin")

        return user
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

def admin_required(user: User = Depends(get_current_user)):
    if user.role != "ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user
