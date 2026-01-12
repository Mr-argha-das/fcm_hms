import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from core.database import init_db
from routes.auth.auth import router as auth_router
from routes.nurse.router import router as nurse_router
from routes.nurse.admin_router import router as admin_nurse_router
from routes.doctor.router import router as doctor_router
from routes.doctor.admin_router import router as admin_doctor_router
from routes.patient.router import router as patient_router
from routes.patient.admin_router import router as admin_patient_router
from routes.relative.router import router as relative_router
from routes.billing.admin_router import router as billing_admin_router
from routes.sos.admin_router import router as sos_admin_router
from routes.complaint.router import router as complaint_router
from routes.complaint.admin_router import router as admin_complaint_router
from routes.notification.router import router as notification_router
from routes.medicine.routes import router as medicine_admin_router
from admin import router as admin_router
from fastapi.middleware.cors import CORSMiddleware
from routes.upload import router as upload_router
from startup import create_default_admin
app = FastAPI(title="Hospital Management System")

init_db()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
      "https://wecarehhcs.in",
      "http://192.0.0.2:8000",
      "http://localhost:8000",
      "http://0.0.0.0:8000",
      "http://10.61.43.98:8000"

    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")
app.include_router(upload_router)
app.include_router(auth_router)
app.include_router(nurse_router)
app.include_router(admin_nurse_router)
app.include_router(doctor_router)
app.include_router(admin_doctor_router)
app.include_router(patient_router)
app.include_router(admin_patient_router)
app.include_router(relative_router)
app.include_router(billing_admin_router)
app.include_router(sos_admin_router)
app.include_router(complaint_router)
app.include_router(admin_complaint_router)
app.include_router(notification_router)
app.include_router(admin_router)
app.include_router(medicine_admin_router)
@app.on_event("startup")
def startup_event():
    create_default_admin()