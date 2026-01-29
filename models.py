
from datetime import datetime , time
from xml.dom.minidom import Document
from mongoengine import *

class User(Document):
    token_version = IntField(default=0)
    role = StringField(
        choices=["ADMIN", "NURSE", "DOCTOR", "PATIENT", "RELATIVE", "STAFF"],
        required=True
    )
    name = StringField(required=False)
    father_name = StringField(required=False)
    phone = StringField(required=True, unique=True)
    other_number = StringField(required=False)
    email = EmailField()
    password_hash = StringField(default="$pbkdf2-sha256$29000$v1fqnbMWQqi1dg4hhJAyJg$i/NU8Lx6vm7TXh5pitQrPvFLS47wHbb8wtKArKmn.NE")     # Admin / Doctor
    otp_verified = BooleanField(default=False)
    
     # ⭐ ADD THIS
    otp_session = StringField()
    is_active = BooleanField(default=True)
    last_login = DateTimeField()

    created_at = DateTimeField(default=datetime.utcnow)

class AboutUs(Document):
    name = StringField()
    designation = StringField()
    description = StringField()
    profile_image = StringField()

    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {"collection": "about_us"}

    
class NurseProfile(Document):
    user = ReferenceField(User, required=True)
    nurse_type = StringField(
        choices=["GNM", "ANM", "CARETAKER", "PHYSIO", "COMBO", "OTHER"]
    )
    aadhaar_front = StringField()
    aadhaar_back = StringField()
    aadhaar_number = StringField()
    aadhaar_verified = BooleanField(default=False)

    qualification_docs = ListField(StringField())
    experience_docs = ListField(StringField())

    profile_photo = StringField()
    digital_signature = StringField()
    digital_signature_verify = BooleanField(default=False)

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
    created_by = StringField(default="ADMIN", required=True)
    created_at = DateTimeField(default=datetime.utcnow)



class NurseLiveLocation(Document):
    nurse = ReferenceField(NurseProfile, required=True)
    latitude = FloatField(required=True)
    longitude = FloatField(required=True)
    updated_at = DateTimeField(default=datetime.utcnow)

class NurseDuty(Document):
    nurse = ReferenceField(NurseProfile)
    patient = ReferenceField("PatientProfile")

    duty_type = StringField(choices=["10HR", "12HR", "24HR", "FLEX"])
    shift = StringField(choices=["DAY", "NIGHT"])
    ward = StringField(required=True)
    room =  StringField(required=True)
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
    method = StringField(choices=["FACE", "MANUAL", "BIOMETRIC"])

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
    nurse = ReferenceField(NurseProfile, required=True)

    # 🔹 Duty Terms (ADMIN SET)
    shift_type = StringField(
        choices=["DAY", "NIGHT", "24_HOURS"],
        required=True
    )
    duty_hours = IntField(required=True)

    # 🔹 Salary (ADMIN CONTROLLED)
    salary_type = StringField(
        choices=["DAILY", "MONTHLY"],
        required=True
    )
    salary_amount = FloatField(required=True)
    payment_mode = StringField(
        choices=["CASH", "BANK", "UPI"],
        required=True
    )
    salary_date = IntField(required=True)  # 1–31

    # 🔹 Legal Acceptances (NURSE ACTION)
    confidentiality_accepted = BooleanField(default=False)
    no_direct_payment_accepted = BooleanField(default=False)
    police_termination_accepted = BooleanField(default=False)

    # 🔹 Proof
    signature_image = StringField()
    consent_pdf = StringField()

    # 🔹 Status Lifecycle
    status = StringField(
        choices=["PENDING", "SIGNED", "REVOKED"],
        default="PENDING"
    )

    # 🔹 Versioning (IMPORTANT)
    version = IntField(default=1)

    # 🔹 Audit Fields
    created_at = DateTimeField(default=datetime.utcnow)
    signed_at = DateTimeField()
    revoked_at = DateTimeField()

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
    address = StringField()
    service_start = DateField()
    service_end = DateField()

    # ✅ NEW FIELD (multiple documents)
    documents = ListField(StringField(), default=list)

class PatientDailyNote(Document):
    patient = ReferenceField(PatientProfile)
    nurse = ReferenceField(NurseProfile)

    note = StringField()
    created_at = DateTimeField(default=datetime.utcnow)

# class PatientVitals(Document):
#     patient = ReferenceField(PatientProfile)

#     bp = StringField()
#     pulse = IntField()
#     spo2 = IntField()
#     temperature = FloatField()
#     sugar = FloatField()

#     recorded_at = DateTimeField(default=datetime.utcnow)

class PatientVitals(Document):
    patient = ReferenceField(PatientProfile, required=True)

    # 🔹 BASIC VITALS
    bp = StringField()                 # 120/80
    pulse = IntField()                 # 72
    spo2 = IntField()                  # 98
    temperature = FloatField()         # 98.6
    o2_level = IntField()              # O2 %
    rbs = FloatField()                 # sugar / random blood sugar

    # 🔹 SUPPORT / DEVICES
    bipap_ventilator = StringField()   # ON / OFF / settings
    iv_fluids = StringField()          # saline / drip details
    suction = StringField()            # yes/no/notes
    feeding_tube = StringField()       # RT/ORAL/PEG

    # 🔹 OUTPUTS
    vomit_aspirate = StringField()
    urine = StringField()
    stool = StringField()

    # 🔹 NOTES
    other = StringField()

    recorded_at = DateTimeField(default=datetime.utcnow)


# class PatientMedication(Document):
#     patient = ReferenceField(PatientProfile)
#     medicine_name = StringField()
#     dosage = StringField()
#     timing = ListField(StringField())
#     duration_days = IntField()
#     price = FloatField(required=False)
class PatientMedication(Document):
    patient = ReferenceField(PatientProfile)

    medicine_name = StringField()
    dosage = StringField()
    timing = ListField(StringField())
    duration_days = IntField()
    price = FloatField(required=False)

    # ✅ correct
    notes = ListField(StringField(), default=list)



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


# class PatientInvoice(Document):
#     patient = ReferenceField(PatientProfile)

#     total_amount = FloatField()
#     paid_amount = FloatField()
#     due_amount = FloatField()

#     invoice_pdf = StringField()
#     status = StringField(choices=["PAID", "PARTIAL", "DUE"])

#     created_at = DateTimeField(default=datetime.utcnow)

class PatientInvoice(Document):
    patient = ReferenceField(PatientProfile)

    invoice_no = StringField(unique=True)   # ✅ only field

    total_amount = FloatField()
    paid_amount = FloatField()
    due_amount = FloatField()

    invoice_pdf = StringField()

    status = StringField(
        choices=["PAID", "PARTIAL", "DUE"],
        default="DUE"
    )

    created_at = DateTimeField(default=datetime.utcnow)


class Complaint(Document):
    raised_by = ReferenceField(User)

    message = StringField()
    status = StringField(choices=["OPEN", "IN_PROGRESS", "RESOLVED"], default="OPEN")

class SOSAlert(Document):
    triggered_by = ReferenceField(User)
    patient = ReferenceField(PatientProfile)
    message = StringField(required=True, default="SOS Alert Triggered")
    location = PointField()
    status = StringField(choices=["ACTIVE", "RESOLVED"], default="ACTIVE")
    created_at = DateTimeField(default=datetime.utcnow)
# class Notification(Document):
#     user = ReferenceField(User)

#     title = StringField()
#     message = StringField()
#     is_read = BooleanField(default=False)

#     created_at = DateTimeField(default=datetime.utcnow)


class Notification(Document):
    user = ReferenceField("User", reverse_delete_rule=NULLIFY)

    title = StringField(required=True)
    message = StringField(required=True)
    is_read = BooleanField(default=False)

    created_at = DateTimeField(default=datetime.utcnow)

# class NurseVisit(Document):
#     nurse = ReferenceField(NurseProfile, required=True)
#     patient = ReferenceField(PatientProfile, required=True)
#     duty = ReferenceField(NurseDuty)
#     ward = StringField()
#     room_no = StringField()
#     visit_type = StringField(
#         choices=["ROUTINE", "MEDICATION", "EMERGENCY", "FOLLOW_UP", "OTHER"],
#     )
    
#     notes = StringField()
#     visit_time = DateTimeField(default=datetime.utcnow)
#     created_by = ReferenceField(User)   # 🔥 IMPORTANT
#     created_at = DateTimeField(default=datetime.utcnow)
class NurseVisit(Document):
    nurse = ReferenceField(NurseProfile, required=True)
    patient = ReferenceField(PatientProfile, required=True)
    duty = ReferenceField(NurseDuty)

    dutyLocation = StringField(
        choices=["HOME", "HOSPITAL"],
        required=True
    )

    ward = StringField()
    room_no = StringField()
    address = StringField()

    visit_type = StringField(
        choices=["ROUTINE", "MEDICATION", "EMERGENCY", "FOLLOW_UP", "OTHER"],
    )

    notes = StringField()
    visit_time = DateTimeField(default=datetime.utcnow)
    created_by = ReferenceField(User)
    created_at = DateTimeField(default=datetime.utcnow)

class DoctorAttendance(Document):
    doctor = ReferenceField(DoctorProfile)
    date = DateField()
    check_in = DateTimeField()
    check_out = DateTimeField()
    method = StringField()
class DoctorSalary(Document):
    doctor = ReferenceField(DoctorProfile)
    month = StringField()
    amount = FloatField()
    is_paid = BooleanField(default=False)
class StaffProfile(Document):
    user = ReferenceField(User)
    staff_type = StringField()   # DRIVER, ATTENDANT, etc
    joining_date = DateField()
class StaffAttendance(Document):
    staff = ReferenceField(StaffProfile)
    date = DateField()
    check_in = DateTimeField()
    check_out = DateTimeField()
class StaffSalary(Document):
    staff = ReferenceField(StaffProfile)
    month = StringField()
    amount = FloatField()


class Medicine(Document):
    name = StringField(required=True)
    company_name = StringField()
    dosage = StringField()          # 500mg, 250mg
    dosage_form = StringField()     # Tablet, Syrup, Injection
    price = FloatField(required=True)

    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)


# class PatientBill(Document):
#     patient = ReferenceField(PatientProfile, required=True)

#     items = EmbeddedDocumentListField(BillItem)

#     sub_total = FloatField()
#     discount = FloatField(default=0)
#     extra_charges = FloatField(default=0)
#     grand_total = FloatField()

#     bill_date = DateTimeField(default=datetime.utcnow)
#     bill_month = StringField()   # YYYY-MM

#     pdf_file = StringField()
#     status = StringField(
#         choices=["UNPAID", "PAID"],
#         default="UNPAID"
#     )

#     created_by = ReferenceField(User)   # ADMIN
#     created_at = DateTimeField(default=datetime.utcnow)


# class BillItem(EmbeddedDocument):
#     title = StringField()
#     quantity = IntField()
#     unit_price = FloatField()
#     total_price = FloatField()
#     dosage = StringField()

#     # 🔹 DATE RANGE
#     start_date = DateField(required=False)
#     till_date = DateField(required=False)

#     # 🔹 AUTO-CALCULATED
#     days = IntField(required=False)

class BillItem(EmbeddedDocument):
    title = StringField()

    quantity = IntField(default=1)
    unit_price = FloatField(default=0)

    # 🔥 base total without GST
    base_total = FloatField(default=0)

    # 🔥 GST
    gst_percent = FloatField(default=0)
    gst_amount = FloatField(default=0)

    # 🔥 final
    total_price = FloatField(default=0)

    dosage = StringField()

    start_date = DateField()
    till_date = DateField()
    days = IntField()

class PatientBill(Document):
    patient = ReferenceField("PatientProfile", required=True)

    items = EmbeddedDocumentListField(BillItem)

    sub_total = FloatField(default=0)     # without GST
    gst_total = FloatField(default=0)     # only GST sum
    total_gst = FloatField(default=0) 

    discount = FloatField(default=0)
    extra_charges = FloatField(default=0)

    grand_total = FloatField(required=True)  # final payable

    status = StringField(default="UNPAID")
    pdf = StringField()

    created_by = ReferenceField("User")
    bill_month = StringField()

    created_at = DateTimeField(default=datetime.utcnow)

# class PatientBill(Document):
#     patient = ReferenceField("PatientProfile", required=True)

#     # 🔥 ITEMS
#     items = EmbeddedDocumentListField(BillItem)
#     sub_total = FloatField(default=0)
#     discount = FloatField(default=0)
#     extra_charges = FloatField(default=0)

#     grand_total = FloatField(required=True)   # final without GST

#     status = StringField(default="UNPAID")
#     pdf = StringField()

#     created_by = ReferenceField("User")
#     bill_month = StringField()

#     created_at = DateTimeField(default=datetime.utcnow)