from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from datetime import datetime
import os
from .schemas import UpdateSalaryRequest

from models import NurseProfile, NurseSalary
from .schemas import (
    CreateSalaryRequest,
    PaySalaryRequest,
    UpdateSalaryRequest,
)
from .utils import (
    parse_month,
    get_working_days,
    get_duty_salary,
    get_nurse_name,
    send_salary_notification,
)
from .payslip_generator import generate_payslip_pdf

router = APIRouter(
    prefix="/api/nurse/salary",
    tags=["💰 Nurse Salary"],
)


# ─────────────────────────────────────────────────────────────
#  HELPER: Payslip banane ke liye data collect karo
# ─────────────────────────────────────────────────────────────

def build_payslip_data(record: NurseSalary, amount_paid_now: float) -> dict:
    nurse = record.nurse

    nurse_name  = "N/A"
    nurse_phone = "N/A"
    nurse_type  = nurse.nurse_type or "N/A"
    nurse_id    = str(nurse.id)

    try:
        nurse_name  = nurse.user.name  or "N/A"
        nurse_phone = nurse.user.phone or "N/A"
    except Exception:
        pass

    hospital_name    = "WeCare360"
    hospital_address = ""
    hospital_phone   = ""

    try:
        hosp = nurse.user.hospital
        if hosp:
            hospital_name    = hosp.name    or "WeCare360"
            hospital_address = hosp.address or ""
            hospital_phone   = hosp.acontact or ""
    except Exception:
        pass

    year, mon = parse_month(record.month)
    attendance = get_working_days(nurse_id, year, mon)
    duty_info  = get_duty_salary(nurse_id, year, mon)

    paid_amount    = record.paid_amount or 0.0
    pending_amount = max((record.net_salary or 0) - paid_amount, 0)

    return {
        "hospital_name"   : hospital_name,
        "hospital_address": hospital_address,
        "hospital_phone"  : hospital_phone,
        "nurse_name"  : nurse_name,
        "nurse_phone" : nurse_phone,
        "nurse_type"  : nurse_type,
        "nurse_id"    : f"NRS-{nurse_id[-6:].upper()}",
        "month"        : record.month,
        "total_days"   : attendance["total_days"],
        "present_days" : attendance["present_days"],
        "absent_days"  : attendance["absent_days"],
        "basic_salary"  : record.basic_salary  or 0,
        "deductions"    : record.deductions     or 0,
        "advance_taken" : record.advance_taken  or 0,
        "net_salary"    : record.net_salary     or 0,
        "amount_paid_now": amount_paid_now,
        "total_paid"     : paid_amount,
        "pending_amount" : pending_amount,
        "is_fully_paid"  : record.is_paid,
        "duty_breakdown" : duty_info["duty_breakdown"],
    }


# ═══════════════════════════════════════════════════════════════
#  1. GET /summary/{nurse_id}?month=YYYY-MM
# ═══════════════════════════════════════════════════════════════

@router.get("/summary/{nurse_id}", summary="Nurse ki salary summary dekho")
def get_salary_summary(
    nurse_id : str,
    month    : str = Query(default=None),
):
    if not month:
        month = datetime.utcnow().strftime("%Y-%m")

    nurse = NurseProfile.objects(id=nurse_id).first()
    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse nahi mili")

    year, mon = parse_month(month)
    attendance = get_working_days(nurse_id, year, mon)
    duty_info  = get_duty_salary(nurse_id, year, mon)

    record = NurseSalary.objects(nurse=nurse_id, month=month).first()

    basic_salary  = record.basic_salary  if record else duty_info["total_calculated_salary"]
    deductions    = record.deductions    if record else 0.0
    advance_taken = record.advance_taken if record else 0.0
    net_salary    = record.net_salary    if record else max(basic_salary - deductions, 0)
    paid_amount   = (record.paid_amount  if record else 0.0) or 0.0
    is_paid       = record.is_paid       if record else False
    payslip_pdf   = record.payslip_pdf   if record else None
    pending       = max(net_salary - paid_amount, 0)

    return {
        "success": True,
        "data": {
            "nurse_id"          : nurse_id,
            "nurse_name"        : get_nurse_name(nurse),
            "month"             : month,
            "total_days"        : attendance["total_days"],
            "present_days"      : attendance["present_days"],
            "absent_days"       : attendance["absent_days"],
            "calculated_salary" : duty_info["total_calculated_salary"],
            "duty_breakdown"    : duty_info["duty_breakdown"],
            "basic_salary"      : basic_salary,
            "deductions"        : deductions,
            "advance_taken"     : advance_taken,
            "net_salary"        : net_salary,
            "total_paid"        : paid_amount,
            "pending_amount"    : pending,
            "is_fully_paid"     : is_paid,
            "payslip_pdf"       : payslip_pdf,
            "salary_record_id"  : str(record.id) if record else None,
        },
    }


# ═══════════════════════════════════════════════════════════════
#  2. POST /create
#
#  ✅ FIX: Agar record exist kare toh 409 nahi, balki existing
#          record ki details return karo taaki /pay use kar sako
# ═══════════════════════════════════════════════════════════════

@router.post("/create", status_code=201, summary="Salary record create karo (ya existing return karo)")
def create_salary(body: CreateSalaryRequest):
    nurse = NurseProfile.objects(id=body.nurse_id).first()
    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse nahi mili")

    # ── FIX: 409 hatao — existing record return karo ──
    existing = NurseSalary.objects(nurse=body.nurse_id, month=body.month).first()
    if existing:
        paid    = existing.paid_amount or 0.0
        pending = max((existing.net_salary or 0) - paid, 0)
        return {
            "success"        : True,
            "already_exists" : True,
            "message"        : "Record pehle se exist karta hai — salary_id se /pay call karo",
            "data": {
                "salary_id"     : str(existing.id),
                "month"         : existing.month,
                "basic_salary"  : existing.basic_salary,
                "deductions"    : existing.deductions,
                "advance_taken" : existing.advance_taken,
                "net_salary"    : existing.net_salary,
                "paid_amount"   : paid,
                "pending"       : pending,
                "is_paid"       : existing.is_paid,
                "payslip_pdf"   : existing.payslip_pdf,
            },
        }

    year, mon = parse_month(body.month)
    attendance = get_working_days(body.nurse_id, year, mon)
    duty_info  = get_duty_salary(body.nurse_id, year, mon)

    basic_salary = body.basic_salary if body.basic_salary > 0 else duty_info["total_calculated_salary"]
    net_salary   = max(basic_salary - body.deductions - body.advance_taken, 0)

    record = NurseSalary(
        nurse         = nurse,
        month         = body.month,
        basic_salary  = basic_salary,
        deductions    = body.deductions,
        advance_taken = body.advance_taken,
        net_salary    = net_salary,
        paid_amount   = 0.0,
        is_paid       = False,
    )
    record.save()

    return {
        "success"        : True,
        "already_exists" : False,
        "message"        : "Salary record create ho gaya",
        "data": {
            "salary_id"     : str(record.id),
            "month"         : body.month,
            "present_days"  : attendance["present_days"],
            "total_days"    : attendance["total_days"],
            "absent_days"   : attendance["absent_days"],
            "basic_salary"  : basic_salary,
            "deductions"    : body.deductions,
            "advance_taken" : body.advance_taken,
            "net_salary"    : net_salary,
            "paid_amount"   : 0.0,
            "pending"       : net_salary,
            "is_paid"       : False,
            "payslip_pdf"   : None,
        },
    }


# ═══════════════════════════════════════════════════════════════
#  3. PUT /pay/{salary_id}
#
#  ✅ Partial ya full — baar baar payment allowed
#  ✅ Har payment pe NAYA payslip generate hoga
#  ✅ Fully paid hone ke baad payment block hogi
# ═══════════════════════════════════════════════════════════════

@router.put(
    "/pay/{salary_id}",
    summary="Salary payment karo — har payment pe naya payslip generate hoga",
    description=(
        "Admin amount dalta hai. "
        "System automatically professional payslip PDF generate karta hai. "
        "Partial ya full dono allowed hai. Baar baar pay kar sakte ho jab tak pending > 0."
    ),
)
def pay_salary(salary_id: str, body: PaySalaryRequest):

    record = NurseSalary.objects(id=salary_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Salary record nahi mila")

    # ── Already fully paid check ──
    if record.is_paid:
        raise HTTPException(
            status_code=400,
            detail={
                "message"    : "Salary pehle se fully paid hai",
                "net_salary" : record.net_salary,
                "total_paid" : record.paid_amount,
                "pending"    : 0,
            },
        )

    current_paid = record.paid_amount or 0.0
    new_paid     = current_paid + body.amount_paid

    # ── Overpayment check ──
    if new_paid > record.net_salary:
        raise HTTPException(
            status_code=400,
            detail={
                "message"        : "Overpayment nahi ho sakti",
                "net_salary"     : record.net_salary,
                "already_paid"   : current_paid,
                "you_are_paying" : body.amount_paid,
                "max_you_can_pay": round(record.net_salary - current_paid, 2),
            },
        )

    # ── Payment update ──
    record.paid_amount = new_paid
    record.is_paid     = (new_paid >= record.net_salary)
    record.save()

    pending = max(record.net_salary - new_paid, 0)

    # ══════════════════════════════════════
    #  AUTO PAYSLIP PDF GENERATE (har baar)
    # ══════════════════════════════════════
    payslip_path = None
    payslip_url  = None

    try:
        print("Generating payslip...")
        slip_data = build_payslip_data(record, body.amount_paid)
        payslip_path = generate_payslip_pdf(slip_data)
        if not payslip_path:
          raise Exception("Payslip path not returned")

        if not os.path.exists(payslip_path):
          raise Exception(f"File not found: {payslip_path}")
        BASE_URL = os.getenv("BASE_URL", "https://wecarehhcs.in")
        payslip_url = f"{BASE_URL}/api/nurse/salary/payslip/{os.path.basename(payslip_path)}"

        # ── Latest payslip URL DB mein save karo ──
        record.payslip_pdf = payslip_url
        record.save()
        print("Payslip saved:", payslip_url)
    except Exception as e:
        print("❌ PAYSLIP ERROR:", str(e))

    # ── Nurse ko notification ──
    send_salary_notification(record.nurse, body.amount_paid, record.month, pending)

    return {
        "success": True,
        "message": (
            "✅ Final payment — salary complete!"
            if record.is_paid
            else f"✅ Partial payment done — ₹{pending} abhi bhi pending hai"
        ),
        "data": {
            "salary_id"       : salary_id,
            "month"           : record.month,
            "net_salary"      : record.net_salary,
            "amount_paid_now" : body.amount_paid,
            "total_paid"      : new_paid,
            "pending_amount"  : pending,
            "is_fully_paid"   : record.is_paid,
            "payslip_pdf"     : payslip_url,
            "payslip_path"    : payslip_path,
        },
    }


# ═══════════════════════════════════════════════════════════════
#  4. GET /payslip/{filename}
# ═══════════════════════════════════════════════════════════════

@router.get(
    "/payslip/{filename}",
    summary="Payslip PDF download karo",
    response_class=FileResponse,
)
def download_payslip(filename: str):
    filepath = os.path.join("media", "payslips", filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Payslip file nahi mili")

    return FileResponse(
        path        = filepath,
        media_type  = "application/pdf",
        filename    = filename,
    )


# ═══════════════════════════════════════════════════════════════
#  5. PUT /update/{salary_id}
# ═══════════════════════════════════════════════════════════════

@router.put("/update/{salary_id}", summary="Salary record update karo")
def update_salary(salary_id: str, body: UpdateSalaryRequest):
    record = NurseSalary.objects(id=salary_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Salary record nahi mila")

    if body.basic_salary  is not None: record.basic_salary  = body.basic_salary
    if body.deductions    is not None: record.deductions     = body.deductions
    if body.advance_taken is not None: record.advance_taken  = body.advance_taken

    record.net_salary = max(
        (record.basic_salary  or 0) -
        (record.deductions    or 0) -
        (record.advance_taken or 0),
        0,
    )

    paid = record.paid_amount or 0.0
    record.is_paid = paid >= record.net_salary
    record.save()

    return {
        "success": True,
        "message": "Salary record update ho gaya",
        "data": {
            "salary_id"     : salary_id,
            "month"         : record.month,
            "basic_salary"  : record.basic_salary,
            "deductions"    : record.deductions,
            "advance_taken" : record.advance_taken,
            "net_salary"    : record.net_salary,
            "total_paid"    : paid,
            "pending_amount": max(record.net_salary - paid, 0),
            "is_fully_paid" : record.is_paid,
            "payslip_pdf"   : record.payslip_pdf,
        },
    }


# ═══════════════════════════════════════════════════════════════
#  6. GET /all/{nurse_id}
# ═══════════════════════════════════════════════════════════════

@router.get("/all/{nurse_id}", summary="Nurse ki poori salary history")
def get_all_salary_history(nurse_id: str):
    nurse = NurseProfile.objects(id=nurse_id).first()
    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse nahi mili")

    records = NurseSalary.objects(nurse=nurse_id).order_by("-month")

    total_earned  = 0.0
    total_paid    = 0.0
    total_pending = 0.0
    history       = []

    for r in records:
        paid    = r.paid_amount or 0.0
        pending = max((r.net_salary or 0) - paid, 0)

        total_earned  += r.net_salary or 0
        total_paid    += paid
        total_pending += pending

        history.append({
            "salary_id"     : str(r.id),
            "month"         : r.month,
            "basic_salary"  : r.basic_salary,
            "deductions"    : r.deductions,
            "advance_taken" : r.advance_taken,
            "net_salary"    : r.net_salary,
            "total_paid"    : paid,
            "pending_amount": pending,
            "is_fully_paid" : r.is_paid,
            "payslip_pdf"   : r.payslip_pdf,
            "created_at"    : r.created_at.isoformat() if r.created_at else None,
        })

    return {
        "success": True,
        "data": {
            "nurse_id"   : nurse_id,
            "nurse_name" : get_nurse_name(nurse),
            "summary": {
                "total_earned"  : total_earned,
                "total_paid"    : total_paid,
                "total_pending" : total_pending,
            },
            "history": history,
        },
    }


# ═══════════════════════════════════════════════════════════════
#  7. GET /pending-list?month=YYYY-MM
# ═══════════════════════════════════════════════════════════════

@router.get("/pending-list", summary="Pending salary wali nurses ki list")
def get_pending_salary_list(
    month: str = Query(default=None,),
):
    if not month:
        month = datetime.utcnow().strftime("%Y-%m")

    records = NurseSalary.objects(month=month, is_paid=False)
    result  = []

    for r in records:
        paid    = r.paid_amount or 0.0
        pending = max((r.net_salary or 0) - paid, 0)

        nurse_id   = "N/A"
        nurse_name = "N/A"
        try:
            nurse_id   = str(r.nurse.id)
            nurse_name = r.nurse.user.name or "N/A"
        except Exception:
            pass

        result.append({
            "salary_id"     : str(r.id),
            "nurse_id"      : nurse_id,
            "nurse_name"    : nurse_name,
            "month"         : r.month,
            "net_salary"    : r.net_salary,
            "total_paid"    : paid,
            "pending_amount": pending,
            "payslip_pdf"   : r.payslip_pdf,
        })

    return {
        "success"              : True,
        "month"                : month,
        "total_pending_nurses" : len(result),
        "data"                 : result,
    }