from fastapi import APIRouter, Depends
from core.dependencies import get_current_user, admin_required
from models import Notification, User

router = APIRouter(prefix="/notification", tags=["Notification"])
@router.get("/my")
def my_notifications(user=Depends(get_current_user)):
    return Notification.objects(user=user)
@router.post("/mark-read")
def mark_read(notification_id: str, user=Depends(get_current_user)):
    n = Notification.objects(id=notification_id, user=user).first()
    n.is_read = True
    n.save()
    return {"message": "Marked as read"}
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
