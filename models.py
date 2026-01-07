
from datetime import datetime , time
from mongoengine import *
class User(Document):
    role = StringField(
        choices=["ADMIN", "NURSE", "DOCTOR", "PATIENT", "RELATIVE"],
        required=True
    )

    phone = StringField(required=True, unique=True)
    email = EmailField()
    password_hash = StringField()     # Admin / Doctor
    otp_verified = BooleanField(default=False)

    is_active = BooleanField(default=True)
    last_login = DateTimeField()

    created_at = DateTimeField(default=datetime.utcnow)

class NurseProfile(Document):
    user = ReferenceField(User, required=True)

    nurse_type = StringField(
        choices=["GNM", "ANM", "CARETAKER", "PHYSIO", "COMBO"]
    )

    aadhaar_number = StringField()
    aadhaar_verified = BooleanField(default=False)

    qualification_docs = ListField(StringField())
    experience_docs = ListField(StringField())

    profile_photo = StringField()
    digital_signature = StringField()

    joining_date = DateField()
    resignation_date = DateField()

    verification_status = StringField(
        choices=["PENDING", "APPROVED", "REJECTED"],
        default="PENDING"
    )

    police_verification_status = StringField(
        choices=["PENDING", "CLEAR", "FAILED"],
        default="PENDING"
    )

    created_at = DateTimeField(default=datetime.utcnow)

class NurseDuty(Document):
    nurse = ReferenceField(NurseProfile)
    patient = ReferenceField("PatientProfile")

    duty_type = StringField(choices=["10HR", "12HR", "24HR", "FLEX"])
    shift = StringField(choices=["DAY", "NIGHT"])

    duty_start = DateTimeField()
    duty_end = DateTimeField()

    check_in = DateTimeField()
    check_out = DateTimeField()
    gps_location = PointField()

    is_active = BooleanField(default=True)
class NurseAttendance(Document):
    nurse = ReferenceField(NurseProfile)
    date = DateField()
    check_in = DateTimeField()
    check_out = DateTimeField()
    method = StringField(choices=["FACE", "MANUAL"])
class NurseSalary(Document):
    nurse = ReferenceField(NurseProfile)

    month = StringField()  # YYYY-MM
    basic_salary = FloatField()
    deductions = FloatField()
    net_salary = FloatField()

    advance_taken = FloatField(default=0)
    is_paid = BooleanField(default=False)
    payslip_pdf = StringField()

    created_at = DateTimeField(default=datetime.utcnow)
class NurseConsent(Document):
    nurse = ReferenceField(NurseProfile)

    shift_type = StringField(choices=["DAY", "NIGHT", "24_HOURS"])
    duty_hours = IntField()

    salary_type = StringField(choices=["DAILY", "MONTHLY"])
    salary_amount = FloatField()
    payment_mode = StringField(choices=["CASH", "BANK", "UPI"])
    salary_date = IntField()

    confidentiality_accepted = BooleanField()
    no_direct_payment_accepted = BooleanField()
    police_termination_accepted = BooleanField()

    signature_image = StringField()
    consent_pdf = StringField()

    status = StringField(choices=["SIGNED", "REVOKED"])
    created_at = DateTimeField(default=datetime.utcnow)
class DoctorProfile(Document):
    user = ReferenceField(User, required=True)

    specialization = StringField()
    registration_number = StringField()
    experience_years = IntField()

    available = BooleanField(default=True)
class DoctorVisit(Document):
    doctor = ReferenceField(DoctorProfile)
    patient = ReferenceField("PatientProfile")

    visit_type = StringField(choices=["ONLINE", "OFFLINE"])
    visit_time = DateTimeField()

    assessment_notes = StringField()
    treatment_plan = StringField()
    prescription_file = StringField()

    created_at = DateTimeField(default=datetime.utcnow)
class PatientProfile(Document):
    user = ReferenceField(User, required=True)

    age = IntField()
    gender = StringField()
    medical_history = StringField()

    assigned_doctor = ReferenceField(DoctorProfile)

    service_start = DateField()
    service_end = DateField()
class PatientDailyNote(Document):
    patient = ReferenceField(PatientProfile)
    nurse = ReferenceField(NurseProfile)

    note = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
class PatientVitals(Document):
    patient = ReferenceField(PatientProfile)

    bp = StringField()
    pulse = IntField()
    spo2 = IntField()
    temperature = FloatField()
    sugar = FloatField()

    recorded_at = DateTimeField(default=datetime.utcnow)
class PatientMedication(Document):
    patient = ReferenceField(PatientProfile)

    medicine_name = StringField()
    dosage = StringField()
    timing = ListField(StringField())
    duration_days = IntField()
class RelativeAccess(Document):
    patient = ReferenceField(PatientProfile)
    relative_user = ReferenceField(User)

    access_type = StringField(
        choices=["FREE", "PAID"],
        default="FREE"
    )

    permissions = ListField(
        StringField(choices=["VITALS", "NOTES", "BILLING"])
    )
class PatientInvoice(Document):
    patient = ReferenceField(PatientProfile)

    total_amount = FloatField()
    paid_amount = FloatField()
    due_amount = FloatField()

    invoice_pdf = StringField()
    status = StringField(choices=["PAID", "PARTIAL", "DUE"])

    created_at = DateTimeField(default=datetime.utcnow)
class Complaint(Document):
    raised_by = ReferenceField(User)
    patient = ReferenceField(PatientProfile)

    message = StringField()
    status = StringField(choices=["OPEN", "IN_PROGRESS", "RESOLVED"])
class SOSAlert(Document):
    triggered_by = ReferenceField(User)
    patient = ReferenceField(PatientProfile)

    location = PointField()
    created_at = DateTimeField(default=datetime.utcnow)
class Notification(Document):
    user = ReferenceField(User)

    title = StringField()
    message = StringField()
    is_read = BooleanField(default=False)

    created_at = DateTimeField(default=datetime.utcnow)

class NurseVisit(Document):
    nurse = ReferenceField(NurseProfile, required=True)
    patient = ReferenceField(PatientProfile, required=True)
    duty = ReferenceField(NurseDuty)

    ward = StringField()
    room_no = StringField()

    visit_type = StringField(
        choices=["ROUTINE", "MEDICATION", "EMERGENCY", "FOLLOW_UP"]
    )

    notes = StringField()
    visit_time = DateTimeField(default=datetime.utcnow)

    created_by = ReferenceField(User)   # 🔥 IMPORTANT
    created_at = DateTimeField(default=datetime.utcnow)