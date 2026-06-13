from dataclasses import dataclass


@dataclass(frozen=True)
class AdminModule:
    key: str
    label: str
    path: str
    icon: str
    prefixes: tuple[str, ...]
    show_in_menu: bool = True


ADMIN_MODULES = [
    AdminModule("dashboard", "Dashboard", "/admin/dashboard", "layout-dashboard", ("/admin/dashboard",)),
    AdminModule("users", "Admin Users", "/admin/users", "shield-check", ("/admin/users", "/admin/user-list")),
    AdminModule("hospital", "Hospital", "/admin/hospital", "hospital", ("/admin/hospital", "/hospital")),
    AdminModule("about", "About Us", "/admin/about", "info", ("/admin/about", "/admin/about-us-get", "/admin/get-update")),
    AdminModule("nurses", "Nurses", "/admin/nurses", "stethoscope", ("/admin/nurses", "/admin/nurse", "/admin/create/nurse", "/nurse/")),
    AdminModule("caretacker", "Caretacker", "/admin/caretacker", "stethoscope", ("/admin/caretacker", "/admin/create/caretacker")),
    AdminModule("self_registered", "Self Registered", "/admin/nurses/self", "file-text", ("/admin/nurses/self",)),
    AdminModule("blocked_nurses", "Blocked Nurse", "/admin/nurses/blocked", "user-x", ("/admin/nurses/blocked",)),
    AdminModule("payments", "Payments", "/admin/payments", "credit-card", ("/admin/payments",)),
    AdminModule("equipment", "Equipment", "/admin/equipment", "wrench", ("/admin/equipment", "/admin/request-equipment", "/patient/assign-equipment")),
    AdminModule("doctors", "Doctors", "/admin/doctors", "stethoscope", ("/admin/doctors", "/admin/create/doctor", "/admin/doctor")),
    AdminModule("patients", "Patients", "/admin/patients", "users", ("/admin/patients", "/admin/create/patient", "/admin/patient")),
    AdminModule("visits", "Visits", "/admin/visit-page", "clipboard-plus", ("/admin/visit-page", "/nurse/visit/create-admin"), False),
    AdminModule("attendance", "Attendance", "/admin/attendance", "calendar-check", ("/admin/attendance",), False),
    AdminModule("salary", "Salary", "/admin/salary", "badge-indian-rupee", ("/admin/salary",), False),
    AdminModule("consent", "Consent", "/admin/consent", "file-check", ("/admin/consent",), False),
    AdminModule("relatives", "Relatives", "/admin/relatives", "users-round", ("/admin/relatives",), False),
    AdminModule("billing", "Billing", "/admin/billing", "file-text", ("/admin/billing", "/billing/admin"), False),
    AdminModule("staff", "Staff", "/admin/staff/manage", "user-cog", ("/admin/staff", "/staff")),
    AdminModule("leads", "Leads", "/admin/lead/create", "user-cog", ("/admin/lead", "/nurse/lead")),
    AdminModule("medicine", "Medicines", "/admin/medicine", "pill", ("/admin/medicine", "/md/admin/medicine")),
    AdminModule("sos", "SOS", "/admin/sos", "alert-triangle", ("/admin/sos", "/sos/admin")),
    AdminModule("complaints", "Complaints", "/admin/complaints", "message-square-warning", ("/admin/complaints", "/complaint/admin")),
    AdminModule("notifications", "Notifications", "/admin/notifications", "bell", ("/admin/notifications", "/admin/send-notification", "/admin/users-notification")),
    AdminModule("exports", "Exports", "/admin/export/excel", "download", ("/admin/export",), False),
]

PUBLIC_ADMIN_PATHS = {"/admin/login"}
MODULE_BY_KEY = {module.key: module for module in ADMIN_MODULES}


def is_super_admin(user) -> bool:
    return getattr(user, "role", None) == "ADMIN" and not getattr(user, "admin_permissions", None)


def get_admin_permissions(user) -> set[str]:
    if getattr(user, "role", None) != "ADMIN":
        return set()
    if is_super_admin(user):
        return {module.key for module in ADMIN_MODULES}
    return set(getattr(user, "admin_permissions", []) or [])


def get_admin_menu(user):
    if getattr(user, "role", None) != "ADMIN":
        return []
    allowed = get_admin_permissions(user)
    return [module for module in ADMIN_MODULES if module.show_in_menu and module.key in allowed]


def module_for_path(path: str) -> str | None:
    matches = []
    for module in ADMIN_MODULES:
        for prefix in module.prefixes:
            if path == prefix or path.startswith(prefix if prefix.endswith("/") else prefix + "/"):
                matches.append((len(prefix), module.key))
    if not matches:
        return None
    return sorted(matches, reverse=True)[0][1]


def user_can_access_admin_path(user, path: str) -> bool:
    if path in PUBLIC_ADMIN_PATHS:
        return True
    if getattr(user, "role", None) != "ADMIN":
        return True
    if is_super_admin(user):
        return True
    required = module_for_path(path)
    if required is None:
        return False
    return required in get_admin_permissions(user)


def first_allowed_admin_path(user) -> str:
    menu = get_admin_menu(user)
    if menu:
        return menu[0].path
    return "/admin/login"
