import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from razorpay.errors import SignatureVerificationError

from core.dependencies import get_current_user
from models import AllPaymentsHistory, NurseProfile, User, UserJoiningFees
from utils.razorpay_client import (
    RAZORPAY_KEY_ID,
    RAZORPAY_KEY_SECRET,
    client,
)

router = APIRouter(prefix="/payments", tags=["payments"])


class CreateOrderRequest(BaseModel):
    userId: str


class VerifyPaymentRequest(BaseModel):
    order_id: str = Field(min_length=1)
    payment_id: str = Field(min_length=1)
    signature: str = Field(min_length=1)


class PriceJoiningAdd(BaseModel):
    amount: int = Field(gt=0)


def _joining_fee() -> UserJoiningFees:
    fee = UserJoiningFees.objects.order_by("-id").first()
    if not fee:
        raise HTTPException(status_code=503, detail="Joining fee is not configured")
    return fee


def _has_successful_payment(user: User) -> bool:
    return AllPaymentsHistory.objects(user=user, status="success").first() is not None


def _payment_state(user: User) -> dict:
    successful = AllPaymentsHistory.objects(
        user=user, status="success"
    ).order_by("-id").first()
    latest = AllPaymentsHistory.objects(user=user).order_by("-id").first()
    payment = successful or latest

    if not payment:
        return {
            "paid": False,
            "status": "not_started",
            "order_id": None,
            "payment_id": None,
        }

    return {
        "paid": successful is not None,
        "status": "success" if successful else payment.status,
        "order_id": payment.order_id,
        "payment_id": payment.payment_id,
    }


def _create_order_for_user(user: User) -> dict:
    if _has_successful_payment(user):
        raise HTTPException(status_code=409, detail="Joining fee is already paid")

    fee = _joining_fee()
    order = client.order.create(
        {
            "amount": fee.amount * 100,
            "currency": "INR",
            "payment_capture": 1,
        }
    )

    AllPaymentsHistory(
        user=user,
        amount=fee,
        status="created",
        order_id=order["id"],
    ).save()

    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order.get("currency", "INR"),
        "key": RAZORPAY_KEY_ID,
    }


@router.post("/create-order")
def create_nurse_order(body: CreateOrderRequest):
    nurse = NurseProfile.objects(id=body.userId).first()
    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse profile not found")
    return _create_order_for_user(nurse.user)


@router.post("/create-order-pataint")
def create_patient_order(user=Depends(get_current_user)):
    return _create_order_for_user(user)


@router.get("/my-status")
def my_payment_status(user=Depends(get_current_user)):
    return _payment_state(user)


@router.get("/get-pataint-trnx")
def get_patient_transaction(user=Depends(get_current_user)):
    state = _payment_state(user)
    # Preserve the old key while making it mean actual successful payment.
    return {"status": state["paid"], **state}


@router.post("/verify-signature")
def verify_payment_signature(payload: VerifyPaymentRequest):
    payment = AllPaymentsHistory.objects(order_id=payload.order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment order not found")

    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": payload.order_id,
                "razorpay_payment_id": payload.payment_id,
                "razorpay_signature": payload.signature,
            }
        )
    except SignatureVerificationError:
        payment.update(status="failed", payment_id=payload.payment_id)
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    payment.update(status="success", payment_id=payload.payment_id)
    return {
        "status": "success",
        "order_id": payload.order_id,
        "payment_id": payload.payment_id,
    }


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None),
):
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing webhook signature")

    body = await request.body()
    expected_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = json.loads(body)
    event = payload.get("event")
    payment_entity = (
        payload.get("payload", {}).get("payment", {}).get("entity", {})
    )
    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")

    if not order_id:
        raise HTTPException(status_code=400, detail="Webhook order ID is missing")

    payment = AllPaymentsHistory.objects(order_id=order_id).first()
    if not payment:
        return {"status": "order_not_found"}

    if event == "payment.captured":
        payment.update(status="success", payment_id=payment_id)
    elif event == "payment.failed":
        payment.update(status="failed", payment_id=payment_id)

    return {"status": "ok"}


@router.get("/status/{order_id}")
def payment_status(order_id: str):
    payment = AllPaymentsHistory.objects(order_id=order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "status": payment.status,
        "order_id": payment.order_id,
        "payment_id": payment.payment_id,
    }


@router.post("/price-joinig-add")
def add_joining_price(body: PriceJoiningAdd):
    UserJoiningFees(amount=body.amount).save()
    return {"status": "ok"}
