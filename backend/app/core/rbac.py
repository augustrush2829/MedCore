from enum import StrEnum


class Role(StrEnum):
    doctor = "doctor"
    pharmacist = "pharmacist"
    admin = "admin"
    auditor = "auditor"
    super_admin = "super_admin"


ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.doctor: {
        "me:read",
        "patient:read",
        "patient:create",
        "case:read",
        "case:create",
        "case:update",
        "ai:run",
        "ai:medication_check",
        "decision:create",
        "feedback:create",
        "audit:case_read",
    },
    Role.pharmacist: {
        "me:read",
        "patient:read",
        "case:read",
        "case:update",
        "case:update_medication",
        "ai:medication_check",
        "audit:case_read",
    },
    Role.admin: {
        "me:read",
        "patient:read",
        "patient:create",
        "case:read",
        "audit:read",
        "user:manage",
        "admin:overview",
        "admin:portal_uploads",
    },
    Role.auditor: {"me:read", "patient:read", "case:read", "audit:read", "audit:case_read"},
    Role.super_admin: {"*"},
}


def has_permission(role: str, permission: str) -> bool:
    role_value = Role(role)
    permissions = ROLE_PERMISSIONS[role_value]
    return "*" in permissions or permission in permissions
