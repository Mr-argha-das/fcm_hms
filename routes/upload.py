# import os
# import uuid
# from fastapi import APIRouter, UploadFile, File, HTTPException

# router = APIRouter(prefix="/upload", tags=["File Upload"])

# BASE_UPLOAD_DIR = "uploads"

# @router.post("/file")
# async def upload_file(
#     file: UploadFile = File(...),
#     folder: str = "documents"   # optional folder name
# ):
#     try:
#         # 1️⃣ Create folder if not exists
#         upload_dir = os.path.join(BASE_UPLOAD_DIR, folder)
#         os.makedirs(upload_dir, exist_ok=True)

#         # 2️⃣ Generate unique filename
#         ext = file.filename.split(".")[-1]
#         unique_name = f"{uuid.uuid4()}.{ext}"

#         file_path = os.path.join(upload_dir, unique_name)

#         # 3️⃣ Save file
#         with open(file_path, "wb") as f:
#             f.write(await file.read())

#         # 4️⃣ Return path
#         return {
#             "success": True,
#             "filename": unique_name,
#             "path": file_path
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
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
        # 1️⃣ Validate file
        if not file.filename or "." not in file.filename:
            raise HTTPException(status_code=400, detail="Invalid file")

        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type .{ext} not allowed"
            )

        # 2️⃣ Ensure ROOT uploads folder exists
        os.makedirs(UPLOAD_ROOT, exist_ok=True)

        # 3️⃣ Ensure sub-folder (documents) exists
        upload_dir = os.path.join(UPLOAD_ROOT, folder)
        os.makedirs(upload_dir, exist_ok=True)

        # 4️⃣ Save file
        unique_name = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(upload_dir, unique_name)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        # 5️⃣ Return public path
        return {
            "success": True,
            "path": f"/uploads/{folder}/{unique_name}"
        }

    except HTTPException:
        raise
    except Exception as e:
        print("UPLOAD ERROR:", e)
        raise HTTPException(status_code=500, detail="File upload failed")
