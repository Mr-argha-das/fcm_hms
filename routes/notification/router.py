# from fastapi import APIRouter, Depends
# from core.dependencies import get_current_user, admin_required
# from models import Notification, User

# router = APIRouter(prefix="/notification", tags=["Notification"])
# @router.get("/my")
# def my_notifications(user=Depends(get_current_user)):
#     return Notification.objects(user=user)
# @router.post("/mark-read")
# def mark_read(notification_id: str, user=Depends(get_current_user)):
#     n = Notification.objects(id=notification_id, user=user).first()
#     n.is_read = True
#     n.save()
#     return {"message": "Marked as read"}
# @router.post("/admin/broadcast")
# def broadcast(title: str, message: str, admin=Depends(admin_required)):
#     users = User.objects(is_active=True)
#     for u in users:
#         Notification(
#             user=u,
#             title=title,
#             message=message
#         ).save()
#     return {"message": "Broadcast sent"}



from fastapi import APIRouter, Depends, Request
from starlette.templating import Jinja2Templates

from core.dependencies import get_current_user, admin_required
from models import Notification, User

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/notification", tags=["Notification"])


# ================= USER NOTIFICATIONS =================

@router.get("/my")
def my_notifications(user=Depends(get_current_user)):
    return Notification.objects(user=user).order_by("-created_at")


@router.post("/mark-read")
def mark_read(notification_id: str, user=Depends(get_current_user)):
    n = Notification.objects(id=notification_id, user=user).first()
    if not n:
        return {"message": "Notification not found"}

    n.is_read = True
    n.save()
    return {"message": "Marked as read"}


# ================= ADMIN BROADCAST =================

@router.post("/admin/broadcast")
def broadcast(title: str, message: str, admin=Depends(admin_required)):
    users = User.objects(is_active=True)

    for u in users:
        Notification(
            user=u,
            title=title,
            message=message
        ).save()

    return {"message": "Broadcast sent"}


# ================= ADMIN API (SAFE DATA) =================

@router.get("/admin/all")
def admin_notifications(admin=Depends(admin_required)):
    notifications = Notification.objects.order_by("-created_at")

    safe_data = []

    for n in notifications:
        try:
            role = n.user.role if n.user else "N/A"
        except Exception:
            role = "N/A"

        safe_data.append({
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "role": role,
            "is_read": n.is_read,
            "created_at": n.created_at
        })

    return safe_data


# ================= ADMIN PAGE =================

@router.get("/admin/notifications")
def notifications_page(
    request: Request,
    admin=Depends(admin_required)
):
    notifications = Notification.objects.order_by("-created_at")

    safe_data = []

    for n in notifications:
        try:
            role = n.user.role if n.user else "N/A"
        except Exception:
            role = "N/A"

        safe_data.append({
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "role": role,
            "is_read": n.is_read,
            "created_at": n.created_at
        })

    return templates.TemplateResponse(
        "admin/notifications.html",
        {
            "request": request,
            "notifications": safe_data
        }
    )
