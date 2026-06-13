import os
from bson import ObjectId
import cv2
import re
import numpy as np
from pydantic import BaseModel
import pytesseract
import json

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse

from aadhaar_service import AadhaarService
aadhaar = AadhaarService() 
from core.dependencies import get_current_user
from models import NurseProfile, User

router = APIRouter(prefix="/adhar", tags=["adhar"])

# ============================================================
# 🔥 ROBUST AADHAAR OCR (FINAL VERSION)
# ============================================================

import requests

def ocr_space_file(filename: str, overlay=False, api_key=None, language="eng"):
    """OCR.space API request with local file."""
    
    if not api_key:
        api_key = "K84530418188957"
    
    payload = {
        "isOverlayRequired": overlay,
        "apikey": api_key,
        "language": language,
    }
    
    with open(filename, "rb") as f:
        r = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": f},
            data=payload,
            timeout=30,
        )
    
    return r.json()


def extract_aadhaar_from_ocr_result(ocr_result: dict) -> str | None:
    """Extract 12-digit Aadhaar from OCR result"""
    try:
        if "ParsedResults" not in ocr_result or not ocr_result["ParsedResults"]:
            print("OCR API ERROR:", ocr_result)
            return None
        
        text = ocr_result["ParsedResults"][0].get("ParsedText", "")
        print("OCR TEXT:", text)
        
        digits = re.sub(r"[^0-9]", "", text)
        match = re.search(r"\d{12}", digits)
        
        return match.group() if match else None
    
    except Exception as e:
        print("OCR PARSE ERROR:", str(e))
        return None


# ============================================================
# 🔹 EXTRACT AADHAAR API
# ============================================================
UPLOAD_TMP_DIR = "/tmp"

@router.post("/extract-aadhaar")
async def extract_aadhaar(file: UploadFile = File(...)):
    """Extract Aadhaar number from uploaded image"""
    try:
        # 1️⃣ Save uploaded file temporarily
        file_path = os.path.join(UPLOAD_TMP_DIR, file.filename)
        
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        print("Saved file to:", file_path)
        
        # 2️⃣ Call OCR.Space
        ocr_result = ocr_space_file(
            filename=file_path,
            language="eng",
            api_key=os.getenv("OCR_API_KEY", "K84530418188957"),
        )
        
        # 3️⃣ Extract Aadhaar
        aadhaar_number = extract_aadhaar_from_ocr_result(ocr_result)
        
        # 4️⃣ Clean up temp file
        try:
            os.remove(file_path)
        except:
            pass
        
        if aadhaar_number:
            return {
                "aadhaar_number": aadhaar_number,
                "method": "ocr_space",
            }
        
        return JSONResponse(
            status_code=404,
            content={"message": "Aadhaar number not found"},
        )
    
    except Exception as e:
        print(f"Extract Aadhaar Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 🔹 GENERATE OTP
# ============================================================

class AadhaarOtpRequest(BaseModel):
    aadhaar_number: str

@router.post("/generate-otp")
def generate(payload: AadhaarOtpRequest):
    """Generate OTP for Aadhaar verification"""
    try:
        result = aadhaar.generate_otp(payload.aadhaar_number)
        print(f"🔥 Generate OTP Response: {json.dumps(result, indent=2)}")
        return result
    except Exception as e:
        print(f"Generate OTP Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 🔹 VERIFY OTP - FIXED VERSION
# ============================================================

class AadhaarVerifyRequest(BaseModel):
    user_id: str
    reference_id: str
    otp: str


def _is_verified_value(value) -> bool:
    """Check if value indicates successful verification"""
    if value is None:
        return False
    
    text = str(value).strip().upper()
    if not text:
        return False
    
    if "INVALID" in text or "FAILED" in text or "EXPIRED" in text:
        return False
    
    return any(
        keyword in text
        for keyword in ["VALID", "VERIFIED", "SUCCESS", "COMPLETED"]
    )


@router.post("/verify-otp")
def verify(payload: AadhaarVerifyRequest):
    """
    Verify OTP and mark Aadhaar as verified
    
    Sandbox API Response Structure:
    {
        "code": 200,
        "data": {
            "reference_id": 74443604,
            "message": "OTP verified successfully",
            "status": "VALID"
        },
        "transaction_id": "..."
    }
    """
    try:
        # 1️⃣ FIX: Properly handle ObjectId conversion
        print(f"🔍 DEBUG - user_id: {payload.user_id}, type: {type(payload.user_id)}")
        
        try:
            # Convert string to ObjectId
            if isinstance(payload.user_id, str):
                user_id = ObjectId(payload.user_id)
            else:
                user_id = payload.user_id
        except Exception as e:
            print(f"❌ ObjectId conversion error: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid user_id format: {str(e)}"
            )
        
        # 2️⃣ Get nurse profile
        user = User.objects.get(id=user_id)
        nurse = NurseProfile.objects.get(user=user)
        
        # 3️⃣ Call Aadhaar service
        print(f"🔥 Verifying with reference_id: {payload.reference_id}, otp: {payload.otp}")
        result = aadhaar.verify_otp(payload.reference_id, payload.otp)
        
        print(f"🔥 Full Verify Response: {json.dumps(result, indent=2)}")
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Invalid response from Aadhaar service"
            )
        
        # 4️⃣ FIX: Correctly parse Sandbox API response structure
        # Sandbox returns: {"code": 200, "data": {...}, "transaction_id": "..."}
        api_code = result.get("code")
        data = result.get("data") or {}
        
        print(f"🔍 API Code: {api_code}")
        print(f"🔍 Data: {json.dumps(data, indent=2)}")
        
        # Collect all verification indicators
        verification_values = [
            api_code,  # Should be 200 for success
            data.get("status"),
            data.get("message"),
            result.get("status"),
            result.get("message"),
            result.get("verification_status"),
        ]
        
        print(f"🔍 Verification values to check: {verification_values}")
        
        # ===== SUCCESS CASE =====
        # Check if code is 200 OR any value indicates success
        is_code_success = api_code == 200
        is_value_success = any(_is_verified_value(value) for value in verification_values)
        
        if is_code_success or is_value_success:
            print("✅ OTP Verification SUCCESS")
            
            nurse.aadhaar_verified = True
            nurse.aadharData = {
                "reference_id": data.get("reference_id") or payload.reference_id,
                "name": data.get("name"),
                "date_of_birth": data.get("date_of_birth"),
                "gender": data.get("gender"),
                "full_address": data.get("full_address"),
                "care_of": data.get("care_of"),
                "photo": data.get("photo"),
            }
            nurse.save()
            
            return {
                "success": True,
                "message": "Aadhaar Verified Successfully",
                "data": nurse.aadharData,
            }
        
        # ===== ERROR CASES =====
        print("❌ OTP Verification FAILED")
        
        msg = (
            data.get("message")
            or result.get("message")
            or data.get("status")
            or result.get("status")
            or "Verification failed"
        )
        
        print(f"Error message: {msg}")
        
        error_map = {
            "Invalid OTP": ("INVALID_OTP", "OTP is incorrect"),
            "OTP Expired": ("OTP_EXPIRED", "OTP has expired, please resend"),
            "Request under process": ("IN_PROGRESS", "Please wait 30 seconds and try again"),
            "Invalid Reference": ("INVALID_REF_ID", "Session expired, please resend OTP"),
        }
        
        # Find matching error
        code = "FAILED"
        message = msg
        
        for key, (err_code, err_msg) in error_map.items():
            if key.lower() in str(msg).lower():
                code = err_code
                message = err_msg
                break
        
        return {
            "success": False,
            "error_code": code,
            "message": message,
        }
    
    except NurseProfile.DoesNotExist as e:
        print(f"❌ Nurse profile not found: {str(e)}")
        raise HTTPException(status_code=404, detail="Nurse profile not found")
    
    except User.DoesNotExist as e:
        print(f"❌ User not found: {str(e)}")
        raise HTTPException(status_code=404, detail="User not found")
    
    except Exception as e:
        print(f"❌ Verify OTP Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))