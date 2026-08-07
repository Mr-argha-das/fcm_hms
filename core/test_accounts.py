"""Explicitly-scoped accounts used for app review and acceptance testing."""

TEST_OTP = "123456"

TEST_ACCOUNTS = {
    "9000000001": "NURSE",
    "9000000002": "PATIENT",
    "9000000003": "DOCTOR",
    "9000000004": "PATIENT",
}

TEST_PAYMENT_EXEMPT_ACCOUNTS = {
    "9000000001",
    "9000000002",
    "9000000003",
}


def is_test_account(phone: str | None, role: str | None = None) -> bool:
    if not phone:
        return False
    expected_role = TEST_ACCOUNTS.get(phone)
    return expected_role is not None and (role is None or expected_role == role)


def is_test_payment_exempt(phone: str | None, role: str | None = None) -> bool:
    if not phone:
        return False
    expected_role = TEST_ACCOUNTS.get(phone)
    return (
        phone in TEST_PAYMENT_EXEMPT_ACCOUNTS
        and expected_role is not None
        and (role is None or expected_role == role)
    )
