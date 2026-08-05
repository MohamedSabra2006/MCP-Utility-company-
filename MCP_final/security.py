"""
Server-side Authorization and Permission Layer
"""
from typing import Dict, Any

ALLOWED_ROLES_FOR_WRITE = ["DISPATCHER", "DISTRICT_SUPERVISOR", "SYS_ADMIN"]
ALLOWED_ROLES_FOR_READ = ["AUDITOR", "DISPATCHER", "DISTRICT_SUPERVISOR", "SYS_ADMIN"]


def verify_user_authorization(session_context: Dict[str, Any], action_type: str) -> tuple[bool, str]:
    """
    Performs server-side permission checks on the active user session.
    """
    user_role = session_context.get("user_role", "GUEST").upper()
    username = session_context.get("username", "Unknown")

    if action_type == "WRITE":
        if user_role not in ALLOWED_ROLES_FOR_WRITE:
            return False, f"Access Denied: Role '{user_role}' for user '{username}' lacks WRITE privileges (DISPATCH_WRITE required)."
    elif action_type == "READ":
        if user_role not in ALLOWED_ROLES_FOR_READ:
            return False, f"Access Denied: Role '{user_role}' lacks read access."
            
    return True, ""
