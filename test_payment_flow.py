import unittest
from unittest.mock import patch

from fastapi import HTTPException
from razorpay.errors import SignatureVerificationError

from routes import payment


class _Query:
    def __init__(self, value):
        self.value = value

    def order_by(self, *_args):
        return self

    def first(self):
        return self.value


class _Manager:
    def __init__(self, successful=None, latest=None, order=None):
        self.successful = successful
        self.latest = latest
        self.order = order

    def __call__(self, **filters):
        if "order_id" in filters:
            return _Query(self.order)
        if filters.get("status") == "success":
            return _Query(self.successful)
        return _Query(self.latest)


class _Payment:
    def __init__(self, status="created", order_id="order_123", payment_id=None):
        self.status = status
        self.order_id = order_id
        self.payment_id = payment_id

    def update(self, **values):
        for key, value in values.items():
            setattr(self, key, value)


class PaymentFlowTests(unittest.TestCase):
    def _model(self, manager):
        return type("FakePaymentModel", (), {"objects": manager})

    def test_created_or_failed_payment_never_grants_access(self):
        user = object()
        for status in ("created", "failed"):
            record = _Payment(status=status)
            with patch.object(
                payment,
                "AllPaymentsHistory",
                self._model(_Manager(latest=record)),
            ):
                state = payment._payment_state(user)
            self.assertFalse(state["paid"])
            self.assertEqual(state["status"], status)

    def test_any_successful_payment_grants_access(self):
        user = object()
        successful = _Payment(status="success", order_id="order_paid")
        failed = _Payment(status="failed", order_id="order_newer")
        with patch.object(
            payment,
            "AllPaymentsHistory",
            self._model(_Manager(successful=successful, latest=failed)),
        ):
            state = payment._payment_state(user)
        self.assertTrue(state["paid"])
        self.assertEqual(state["status"], "success")
        self.assertEqual(state["order_id"], "order_paid")

    def test_valid_checkout_signature_marks_payment_successful(self):
        record = _Payment()
        payload = payment.VerifyPaymentRequest(
            order_id="order_123", payment_id="pay_123", signature="valid"
        )
        with (
            patch.object(
                payment,
                "AllPaymentsHistory",
                self._model(_Manager(order=record)),
            ),
            patch.object(payment.client.utility, "verify_payment_signature"),
        ):
            result = payment.verify_payment_signature(payload)
        self.assertEqual(result["status"], "success")
        self.assertEqual(record.status, "success")
        self.assertEqual(record.payment_id, "pay_123")

    def test_invalid_checkout_signature_marks_payment_failed(self):
        record = _Payment()
        payload = payment.VerifyPaymentRequest(
            order_id="order_123", payment_id="pay_bad", signature="invalid"
        )
        with (
            patch.object(
                payment,
                "AllPaymentsHistory",
                self._model(_Manager(order=record)),
            ),
            patch.object(
                payment.client.utility,
                "verify_payment_signature",
                side_effect=SignatureVerificationError("bad signature"),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                payment.verify_payment_signature(payload)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(record.status, "failed")


if __name__ == "__main__":
    unittest.main()
