import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter(prefix="/upload", tags=["File Upload"])

# ✅ PROJECT ROOT
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_ROOT = os.path.join(BASE_DIR, "uploads")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}

@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    folder: str = "documents"
):
    try:
        print("👉 Upload API hit")
        print("Filename:", file.filename)

        upload_dir = os.path.join(UPLOAD_ROOT, folder)
        os.makedirs(upload_dir, exist_ok=True)

        # 🔥 TEMP: allow all extensions
        ext = "bin"
        if file.filename and "." in file.filename:
            ext = file.filename.rsplit(".", 1)[-1].lower()

        unique_name = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(upload_dir, unique_name)

        data = await file.read()
        print("FILE SIZE:", len(data))

        with open(file_path, "wb") as f:
            f.write(data)

        return {
            "success": True,
            "path": f"/uploads/{folder}/{unique_name}"
        }

    except Exception as e:
        print("🔥 UPLOAD ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/file")
# async def upload_file(
#     file: UploadFile = File(...),
#     folder: str = "documents"
# ):
#     try:
#         print("👉 Upload API hit")
#         print("Filename:", file.filename)
#         print("Folder:", folder)
#         print("UPLOAD_ROOT:", UPLOAD_ROOT)

#         # ✅ CORRECT upload directory
#         upload_dir = os.path.join(UPLOAD_ROOT, folder)
#         print("UPLOAD_DIR:", upload_dir)

#         os.makedirs(upload_dir, exist_ok=True)

#         if not file.filename or "." not in file.filename:
#             raise HTTPException(status_code=400, detail="Invalid file")

#         ext = file.filename.rsplit(".", 1)[-1].lower()
#         if ext not in ALLOWED_EXTENSIONS:
#             raise HTTPException(status_code=400, detail="Invalid file type")

#         unique_name = f"{uuid.uuid4()}.{ext}"
#         file_path = os.path.join(upload_dir, unique_name)

#         print("FILE_PATH:", file_path)

#         data = await file.read()
#         print("FILE SIZE:", len(data))

#         with open(file_path, "wb") as f:
#             f.write(data)

#         return {
#             "success": True,
#             "path": f"/uploads/{folder}/{unique_name}"
#         }

#     except Exception as e:
#         print("🔥 UPLOAD ERROR:", repr(e))
#         raise HTTPException(status_code=500, detail="File upload failed")

