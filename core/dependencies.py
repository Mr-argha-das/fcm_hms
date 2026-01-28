from fastapi import Depends, HTTPException, status , Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from core.security import SECRET_KEY, ALGORITHM
from models import User

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login-password")

# def get_current_user(token: str = Depends(oauth2_scheme)):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id = payload.get("user_id")

#         user = User.objects(id=user_id).first()
#         if not user:
#             raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

#         if not user.is_active:
#             raise HTTPException(status.HTTP_403_FORBIDDEN, "User blocked by admin")

#         return user
#     except JWTError:
#         raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login-password",
    auto_error=False
)

def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme)
):

    try:
        # 🔥 header nahi mila to cookie se lo
        if not token:
            token = request.cookies.get("access_token")

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        user = User.objects(id=user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User blocked by admin"
            )

        return user

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

def get_current_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        user = User.objects(id=user_id).first()
        if not user:
            raise HTTPException(status_code=401)

        if not user.is_active:
            raise HTTPException(status_code=403)

        return user

    except JWTError:
        raise HTTPException(status_code=401)

def admin_required(user: User = Depends(get_current_user)):
    if user.role != "ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


def role_required(allowed_roles: list):
    def wrapper(user = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        return user
    return wrapper