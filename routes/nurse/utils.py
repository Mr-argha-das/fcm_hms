# nurse/utils.py
from fastapi import HTTPException
from datetime import datetime
from models import NurseConsent

def ensure_consent_active(nurse):
    consent = NurseConsent.objects(nurse=nurse, status="SIGNED").first()
    if not consent:
        raise HTTPException(403, "Active consent required")

def ensure_duty_time(duty):
    now = datetime.utcnow()
    if not (duty.duty_start <= now <= duty.duty_end):
        raise HTTPException(403, "Outside duty time")

from datetime import datetime, date
import calendar
from fastapi import HTTPException


def parse_month(month_str: str) -> tuple:
    """
    'YYYY-MM' string ko (year, month) tuple mein convert karo.
    Invalid format par 400 error dega.
    """
    try:
        year, month = map(int, month_str.split("-"))
        if not (1 <= month <= 12):
            raise ValueError
        return year, month
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="month format galat hai. YYYY-MM use karein. Example: 2025-06"
        )


def get_working_days(nurse_id: str, year: int, month: int) -> dict:
    """
    NurseAttendance collection se us month ke present days calculate karo.
    Sirf woh records count honge jisme check_in AND check_out dono hain.
    """
    from models import NurseAttendance

    total_days = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date   = date(year, month, total_days)

    attendances = NurseAttendance.objects(
        nurse=nurse_id,
        date__gte=start_date,
        date__lte=end_date,
    )

    present_days = sum(1 for a in attendances if a.check_in and a.check_out)

    return {
        "total_days"   : total_days,
        "present_days" : present_days,
        "absent_days"  : total_days - present_days,
    }


def get_duty_salary(nurse_id: str, year: int, month: int) -> dict:
    """
    NurseDuty collection se us month ki calculated salary nikalo.
    price_perday × (days active in that month) formula use hoga.
    Multiple duties ka alag-alag breakdown milega.
    """
    from models import NurseDuty

    last_day = calendar.monthrange(year, month)[1]
    start_dt = datetime(year, month, 1)
    end_dt   = datetime(year, month, last_day, 23, 59, 59)

    duties = NurseDuty.objects(
        nurse=nurse_id,
        duty_start__lte=end_dt,
        duty_end__gte=start_dt,
    )

    total_salary   = 0.0
    duty_breakdown = []

    for duty in duties:
        price_perday = duty.price_perday or 0.0

        # Us month ke andar kitne days active tha ye duty
        d_start = max(duty.duty_start, start_dt) if duty.duty_start else start_dt
        d_end   = min(duty.duty_end,   end_dt)   if duty.duty_end   else end_dt
        days    = max((d_end - d_start).days + 1, 0)

        salary_for_duty = price_perday * days
        total_salary   += salary_for_duty

        duty_breakdown.append({
            "duty_id"      : str(duty.id),
            "duty_type"    : duty.duty_type,
            "shift"        : duty.shift,
            "price_perday" : price_perday,
            "days"         : days,
            "salary"       : salary_for_duty,
        })

    return {
        "total_calculated_salary" : total_salary,
        "duty_breakdown"          : duty_breakdown,
    }


def get_nurse_name(nurse) -> str:
    """Nurse ka naam safely fetch karo."""
    try:
        return nurse.user.name or "N/A"
    except Exception:
        return "N/A"


def send_salary_notification(nurse, amount: float, month: str, pending: float):
    """
    Salary payment hone par nurse ko notification bhejo.
    Error aane par silently fail hoga — main flow nahi tutega.
    """
    from models import Notification
    try:
        Notification(
            user    = nurse.user,
            title   = "Salary Credit 💰",
            message = (
                f"Aapko ₹{amount:,.0f} ki salary credit hui hai. "
                f"Month: {month}. "
                f"Baaki pending: ₹{pending:,.0f}."
            ),
        ).save()
    except Exception:
        pass