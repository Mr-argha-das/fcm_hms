import os
from core.dependencies import get_current_user, get_current_user_from_cookie
from fastapi import FastAPI , Depends ,Request
from fastapi.responses import RedirectResponse

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
from routes.auth.about_us_routes import router as about_router
from admin import router as admin_router
from fastapi.middleware.cors import CORSMiddleware
from routes.upload import router as upload_router
from routes.digikey.digikey_routes import router as digikey_router

from routes.staff.routes import router as staff_router

from jose import JWTError
from startup import create_default_admin
app = FastAPI(title="Hospital Management System")


init_db()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "https://wecarehhcs.in"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/documents", exist_ok=True)

@app.middleware("http")
async def admin_auth_guard(request: Request, call_next):

    path = request.url.path

    if path.startswith("/admin") and path not in ["/admin/login"]:
        try: 
            user = get_current_user_from_cookie(request)
            request.state.user = user
        except:
            return RedirectResponse("/admin/login")

    return await call_next(request)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")
# app.include_router(upload_router)
app.include_router(about_router)
app.include_router(digikey_router)
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
app.include_router(staff_router)

@app.on_event("startup")
def startup_event():
    create_default_admin()