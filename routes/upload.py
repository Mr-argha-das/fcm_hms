import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter(prefix="/upload", tags=["File Upload"])

BASE_UPLOAD_DIR = "uploads"

@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    folder: str = "documents"   # optional folder name
):
    try:
        # 1️⃣ Create folder if not exists
        upload_dir = os.path.join(BASE_UPLOAD_DIR, folder)
        os.makedirs(upload_dir, exist_ok=True)

        # 2️⃣ Generate unique filename
        ext = file.filename.split(".")[-1]
        unique_name = f"{uuid.uuid4()}.{ext}"

        file_path = os.path.join(upload_dir, unique_name)

        # 3️⃣ Save file
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # 4️⃣ Return path
        return {
            "success": True,
            "filename": unique_name,
            "path": file_path
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
