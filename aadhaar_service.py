import requests
import os
import json
from token_manager import token_manager

BASE_URL = "https://api.sandbox.co.in"


class AadhaarService:
    
    def __init__(self):
        self.api_key = "key_live_596d1cc1a8ec4cf4972d2a3847649041"
        self.api_secret = "secret_live_fdab340fc4704fd2bb18295563b158cc"
    
    def _headers(self):
        """Generate request headers with auth token"""
        token = token_manager.get_token()
        
        return {
            "Authorization": token,
            "x-api-key": self.api_key,
            'x-api-version': '1.0',
            "Content-Type": "application/json"
        }
    
    # 🔥 STEP 1 → Generate OTP
    def generate_otp(self, aadhaar_number, reason="Verification"):
        """
        Generate OTP for Aadhaar verification
        
        Response:
        {
            "code": 200,
            "timestamp": 1775746774951,
            "data": {
                "@entity": "in.co.sandbox.kyc.aadhaar.okyc.otp.response",
                "reference_id": 74443604,
                "message": "OTP sent successfully"
            },
            "transaction_id": "da89833e-4ffa-44f7-b311-acbc29823390"
        }
        """
        url = f"{BASE_URL}/kyc/aadhaar/okyc/otp"
        
        payload = {
            "@entity": "in.co.sandbox.kyc.aadhaar.okyc.otp.request",
            "aadhaar_number": str(aadhaar_number),
            "consent": "Y",
            "reason": reason
        }
        
        try:
            print(f"📤 Generate OTP Payload: {json.dumps(payload, indent=2)}")
            
            res = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=10
            )
            
            print(f"📥 Status Code: {res.status_code}")
            print(f"📥 Raw Response: {res.text}")
            
            if res.status_code == 200:
                response_data = res.json()
                print(f"📥 JSON Response: {json.dumps(response_data, indent=2)}")
                return response_data
            else:
                error_response = {
                    "code": res.status_code,
                    "message": f"API Error: {res.status_code}",
                    "body": res.text
                }
                print(f"❌ Error Response: {json.dumps(error_response, indent=2)}")
                return error_response
        
        except requests.exceptions.Timeout:
            error = {"code": 504, "message": "Request timeout"}
            print(f"❌ Timeout: {error}")
            return error
        
        except requests.exceptions.RequestException as e:
            error = {"code": 500, "message": f"Network error: {str(e)}"}
            print(f"❌ Network Error: {error}")
            return error
        
        except Exception as e:
            error = {"code": 500, "message": f"Error: {str(e)}"}
            print(f"❌ Exception: {error}")
            return error
    
    # 🔥 STEP 2 → Verify OTP - FIXED VERSION
    def verify_otp(self, reference_id, otp):
        """
        Verify OTP sent to user
        
        Response on Success:
        {
            "code": 200,
            "data": {
                "status": "VALID",
                "message": "OTP verified successfully",
                "reference_id": 74443604
            },
            "transaction_id": "..."
        }
        
        Response on Invalid OTP:
        {
            "code": 400,
            "data": {
                "status": "INVALID",
                "message": "Invalid OTP"
            }
        }
        """
        url = f"{BASE_URL}/kyc/aadhaar/okyc/otp/verify"
        
        payload = {
            "@entity": "in.co.sandbox.kyc.aadhaar.okyc.request",
            "reference_id": str(reference_id),  # Ensure string format
            "otp": str(otp)
        }
        
        try:
            print(f"📤 Verify OTP Payload: {json.dumps(payload, indent=2)}")
            
            res = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=10
            )
            
            print(f"📥 Verify Status Code: {res.status_code}")
            print(f"📥 Verify Raw Response: {res.text}")
            
            # Always return JSON response, even on error
            try:
                response_data = res.json()
            except:
                response_data = {
                    "code": res.status_code,
                    "message": f"Failed to parse response: {res.text}"
                }
            
            print(f"📥 Verify JSON Response: {json.dumps(response_data, indent=2)}")
            return response_data
        
        except requests.exceptions.Timeout:
            error = {
                "code": 504,
                "data": {"message": "Request timeout"},
                "message": "Timeout"
            }
            print(f"❌ Verify Timeout: {error}")
            return error
        
        except requests.exceptions.RequestException as e:
            error = {
                "code": 500,
                "data": {"message": f"Network error: {str(e)}"},
                "message": f"Network error: {str(e)}"
            }
            print(f"❌ Verify Network Error: {error}")
            return error
        
        except Exception as e:
            error = {
                "code": 500,
                "data": {"message": f"Error: {str(e)}"},
                "message": f"Error: {str(e)}"
            }
            print(f"❌ Verify Exception: {error}")
            return error