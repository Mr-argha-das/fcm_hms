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
