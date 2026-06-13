import os
from core.dependencies import get_current_user, get_current_user_from_cookie
from fastapi import FastAPI , Depends ,Request
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse

from fastapi.staticfiles import StaticFiles
from core.database import init_db
from routes.auth.auth import router as auth_router
from routes.nurse.router import router as nurse_router
from routes.nurse.admin_router import router as admin_nurse_router
from routes.doctor.router import router as doctor_router
from routes.doctor.admin_router import router as admin_doctor_router
from routes.patient.router import router as patient_router ,equipment_router
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
from routes.sheet.routes import router as sheetRouter
from routes.staff.routes import router as staff_router
from routes.fcm.routes.routes import router as notifcationRouter
from routes.payment import router as paymentRouter
from routes.hospital.routes import router as hospital_router
from routes.adhar.routes import router as aadharRouter
from routes.nurse.pdfSalaryRouter import router as pdfSalaryRouter  
from jose import JWTError, jwt
from startup import create_default_admin
from core.permissions import first_allowed_admin_path, module_for_path, user_can_access_admin_path
from core.security import SECRET_KEY, ALGORITHM
from models import User
app = FastAPI(title="Hospital Management System")


init_db()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://192.0.0.2:8000",
        "https://wecarehhcs.in",
        # "https://7cdss4vm-8005.inc1.devtunnels.ms"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_PREFIXES = (
    "/payments",
    "/docs",
    "/openapi.json"
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/documents", exist_ok=True)

@app.middleware("http")
async def admin_auth_guard(request: Request, call_next):
    path = request.url.path

    # 🔥 PUBLIC ROUTES → NO AUTH, NO COOKIE, NO REDIRECT
    if path.startswith(PUBLIC_PREFIXES):
        return await call_next(request)

    # 🔒 ADMIN ROUTES ONLY
    if path.startswith("/admin") and path != "/admin/login":
        try:
            user = get_current_user_from_cookie(request)
            request.state.user = user
            if not user_can_access_admin_path(user, path):
                if request.method == "GET":
                    return RedirectResponse(first_allowed_admin_path(user))
                return RedirectResponse("/admin/login", status_code=303)
        except Exception as e:
            print("Admin auth error:", e)
            return RedirectResponse("/admin/login")

    required_module = module_for_path(path)
    if required_module and not path.startswith("/admin"):
        token = request.cookies.get("access_token")
        auth_header = request.headers.get("authorization") or ""
        if not token and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]

        if token:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user = User.objects(id=payload.get("user_id")).first()
                if user and user.role == "ADMIN" and not user_can_access_admin_path(user, path):
                    return JSONResponse(
                        {"detail": "You do not have permission for this module"},
                        status_code=403
                    )
            except JWTError:
                pass

    return await call_next(request)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")
app.include_router(equipment_router)
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
app.include_router(sheetRouter)
app.include_router(notifcationRouter)
app.include_router(paymentRouter)
app.include_router(hospital_router)
app.include_router(aadharRouter)
app.include_router(pdfSalaryRouter)
@app.get("/download/download-apk")
def download_apk():
    file_path = "apk/app-release.apk"
    return FileResponse(
        path=file_path,
        filename="app-release.apk",
        media_type="application/vnd.android.package-archive"
    )

from datetime import datetime
import pytz

@app.get("/check-time")
def check_time():
    ist = pytz.timezone("Asia/Kolkata")

    return {
        "utc_time": datetime.utcnow().isoformat(),
        "server_time": datetime.now().isoformat(),
        "ist_time": datetime.now(ist).isoformat()
    }

@app.on_event("startup")
def startup_event():
    create_default_admin()
