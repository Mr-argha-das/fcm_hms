from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from models import User
from ..fcm import send_bulk_push
router = APIRouter(prefix="/admin")

class PushRequest(BaseModel):
    title: str
    body: str
    role: Optional[str] = None
    user_ids: Optional[List[str]] = None
    send_all: bool = False


@router.post("/send-notification")
def send_notification(req: PushRequest):

    # 🎯 CASE 1 → selected users
    if req.user_ids:
        users = User.objects(id__in=req.user_ids, token__ne=None)

    # 🎯 CASE 2 → role based all
    elif req.role and not req.send_all:
        users = User.objects(role=req.role, token__ne=None)

    # 🎯 CASE 3 → all users
    else:
        users = User.objects(token__ne=None)

    tokens = [u.token for u in users if u.token]

    send_bulk_push(tokens, req.title, req.body)

    return {
        "sent_to": len(tokens),
        "message": "Notification sent successfully"
    }

@router.get("/users-notification")
def get_users(role: str = Query(None)):
    query = {}

    if role and role != "ALL":
        query["role"] = role

    users = User.objects(**query).only("id", "name", "phone", "role")

    return [
        {
            "id": str(u.id),
            "name": u.name,
            "phone": u.phone,
            "role": u.role
        }
        for u in users
    ]