# app/startup.py

from models import User
from core.config import (
    DEFAULT_ADMIN_PHONE,
    DEFAULT_ADMIN_EMAIL,
    DEFAULT_ADMIN_PASSWORD
)
from core.security import hash_password
from datetime import datetime

def create_default_admin():
    # 🔍 Check if admin already exists
    admin = User.objects(
        role="ADMIN",
        phone=DEFAULT_ADMIN_PHONE
    ).first()

    if admin:
        print("✅ Default admin already exists")
        return

    # 🧑‍💼 Create admin
    User(
        role="ADMIN",
        phone=DEFAULT_ADMIN_PHONE,
        email=DEFAULT_ADMIN_EMAIL,
        password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
        otp_verified=True,
        is_active=True,
        created_at=datetime.utcnow()
    ).save()

    print("🔥 Default admin created successfully")
