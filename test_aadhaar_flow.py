import unittest
from unittest.mock import patch

from routes.adhar import routes


class _Manager:
    def __init__(self, value):
        self.value = value

    def get(self, **_kwargs):
        return self.value


class _FakeNurse:
    def __init__(self):
        self.aadhaar_verified = False
        self.aadhaar_number = None
        self.aadharData = None
        self.saved = False

    def save(self):
        self.saved = True


class AadhaarFlowTests(unittest.TestCase):
    def setUp(self):
        self.user = object()
        self.nurse = _FakeNurse()

        class FakeUserModel:
            DoesNotExist = type("UserDoesNotExist", (Exception,), {})
            objects = _Manager(self.user)

        class FakeNurseModel:
            DoesNotExist = type("NurseDoesNotExist", (Exception,), {})
            objects = _Manager(self.nurse)

        self.model_patches = (
            patch.object(routes, "User", FakeUserModel),
            patch.object(routes, "NurseProfile", FakeNurseModel),
        )
        for model_patch in self.model_patches:
            model_patch.start()

    def tearDown(self):
        for model_patch in reversed(self.model_patches):
            model_patch.stop()

    def _payload(self):
        return routes.AadhaarVerifyRequest(
            user_id="507f1f77bcf86cd799439011",
            reference_id="74443604",
            otp="123456",
            aadhaar_number="123456789012",
        )

    def test_valid_otp_marks_nurse_verified(self):
        provider_response = {
            "code": 200,
            "data": {
                "status": "VALID",
                "message": "OTP verified successfully",
                "reference_id": "74443604",
            },
        }

        with patch.object(routes.aadhaar, "verify_otp", return_value=provider_response):
            result = routes.verify(self._payload())

        self.assertTrue(result["success"])
        self.assertTrue(self.nurse.aadhaar_verified)
        self.assertEqual(self.nurse.aadhaar_number, "123456789012")
        self.assertTrue(self.nurse.saved)

    def test_http_200_with_invalid_status_is_not_success(self):
        provider_response = {
            "code": 200,
            "data": {"status": "INVALID", "message": "Invalid OTP"},
        }

        with patch.object(routes.aadhaar, "verify_otp", return_value=provider_response):
            result = routes.verify(self._payload())

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "INVALID_OTP")
        self.assertFalse(self.nurse.aadhaar_verified)
        self.assertFalse(self.nurse.saved)

    def test_expired_otp_returns_specific_error(self):
        provider_response = {
            "code": 400,
            "data": {"status": "EXPIRED", "message": "OTP Expired"},
        }

        with patch.object(routes.aadhaar, "verify_otp", return_value=provider_response):
            result = routes.verify(self._payload())

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "OTP_EXPIRED")

    def test_request_validation_rejects_bad_values(self):
        with self.assertRaises(ValueError):
            routes.AadhaarOtpRequest(aadhaar_number="1234")
        with self.assertRaises(ValueError):
            routes.AadhaarVerifyRequest(
                user_id="null",
                reference_id="74443604",
                otp="12345",
            )


if __name__ == "__main__":
    unittest.main()
