import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

_TIMEOUT = 10


def _get_headers():
    """Attach the JWT Bearer token from session state to every API call."""
    token = st.session_state.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


# -- Auth --

def authenticate_user(email: str, password: str):
    """Authenticate an admin or moderator and return the raw response."""
    return requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"EmailAddress": email, "Password": password, "ClientType": "web"},
        timeout=_TIMEOUT,
    )


# -- System Health --

def check_backend_health():
    """Return the raw response from the backend root health endpoint."""
    return requests.get(f"{BACKEND_URL}/", headers=_get_headers(), timeout=_TIMEOUT)


def fetch_system_health():
    """Fetch detailed system health stats (admin only)."""
    response = requests.get(f"{BACKEND_URL}/api/health", headers=_get_headers(), timeout=_TIMEOUT)
    return response.json() if response.status_code == 200 else None


# -- Blacklist Requests (Moderation) --

# -- User Accounts --

def fetch_all_users():
    """Return all user accounts."""
    response = requests.get(f"{BACKEND_URL}/api/accounts/", params={"limit": 10000}, headers=_get_headers(), timeout=_TIMEOUT)
    return response.json() if response.status_code == 200 else []


def deactivate_user(user_id: int):
    """Set a user account to inactive."""
    response = requests.put(
        f"{BACKEND_URL}/api/accounts/{user_id}",
        json={"IsActive": False},
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200


def activate_user(user_id: int):
    """Set a user account to active."""
    response = requests.put(
        f"{BACKEND_URL}/api/accounts/{user_id}",
        json={"IsActive": True},
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200


def update_user_details(user_id: int, payload: dict):
    """Update account-level fields (EmailAddress, RoleID, IsActive)."""
    response = requests.put(
        f"{BACKEND_URL}/api/accounts/{user_id}",
        json=payload,
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200


# -- User Details --

def fetch_user_detail(user_id: int):
    """Return profile details for a single user, or None if not found."""
    response = requests.get(
        f"{BACKEND_URL}/api/details/{user_id}", headers=_get_headers(), timeout=_TIMEOUT
    )
    return response.json() if response.status_code == 200 else None


def update_user_profile(user_id: int, payload: dict):
    """Update user details (FullName, PhoneNumber, Address, Gender, DateOfBirth)."""
    response = requests.put(
        f"{BACKEND_URL}/api/details/{user_id}",
        json=payload,
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200


# -- App Feedback --

def fetch_app_feedback():
    """Return all app feedback submissions."""
    response = requests.get(f"{BACKEND_URL}/api/feedback/", headers=_get_headers(), timeout=_TIMEOUT)
    return response.json() if response.status_code == 200 else []


# -- Action History --

def fetch_action_history():
    """Return all audit log entries."""
    response = requests.get(f"{BACKEND_URL}/api/history/", headers=_get_headers(), timeout=_TIMEOUT)
    return response.json() if response.status_code == 200 else []


def log_action(user_id: int, action_type: str, action: str):
    """Insert an audit log entry. Silently ignores failures — logging is non-critical."""
    try:
        requests.post(
            f"{BACKEND_URL}/api/history/",
            json={"UserID": user_id, "ActionType": action_type, "Action": action},
            headers=_get_headers(),
            timeout=_TIMEOUT,
        )
    except Exception:
        pass


# -- URL Rules --

def fetch_url_rules():
    """Return all URL blacklist and whitelist rules."""
    response = requests.get(f"{BACKEND_URL}/api/url-rules/", params={"limit": 10000}, headers=_get_headers(), timeout=_TIMEOUT)
    return response.json() if response.status_code == 200 else []


def create_url_rule(domain: str, list_type: str, added_by: int):
    """Add a domain to the blacklist or whitelist."""
    response = requests.post(
        f"{BACKEND_URL}/api/url-rules/",
        json={"URLDomain": domain, "ListType": list_type, "AddedBy": added_by},
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 201


def delete_url_rule(rule_id: int):
    """Delete a URL rule by ID."""
    response = requests.delete(
        f"{BACKEND_URL}/api/url-rules/{rule_id}", headers=_get_headers(), timeout=_TIMEOUT
    )
    return response.status_code == 204


# -- Scan History --

def scan_url(url: str) -> dict | None:
    """Submit a URL to the scan pipeline and return the result, or None on failure.
    Timeout is 120 s — the scan pipeline can take up to ~90 s."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/scan",
            json={"urls": url},
            headers=_get_headers(),
            timeout=120,
        )
        if response.status_code == 200:
            results = response.json()
            return results[0] if results else None
    except Exception:
        pass
    return None


def fetch_scan_list(skip: int = 0, limit: int = 25, search: str = None,
                    status_indicator: str = None, user_id: int = None):
    """Fetch paginated scan history with optional filters."""
    params = {"skip": skip, "limit": limit}
    if search:
        params["search"] = search
    if status_indicator:
        params["status_indicator"] = status_indicator
    if user_id:
        params["user_id"] = user_id
    response = requests.get(
        f"{BACKEND_URL}/api/scans/", params=params, headers=_get_headers(), timeout=_TIMEOUT
    )
    return response.json() if response.status_code == 200 else []


def fetch_scan_details(scan_id: int):
    """Return full details for a single scan record."""
    response = requests.get(
        f"{BACKEND_URL}/api/scans/{scan_id}", headers=_get_headers(), timeout=_TIMEOUT
    )
    return response.json() if response.status_code == 200 else None


# -- Scan Feedback --

def fetch_scan_feedback(is_resolved: bool = None):
    """Return scan feedback submissions, optionally filtered by resolution status."""
    params = {}
    if is_resolved is not None:
        params["is_resolved"] = str(is_resolved).lower()
    response = requests.get(
        f"{BACKEND_URL}/api/scan-feedback/", params=params, headers=_get_headers(), timeout=_TIMEOUT
    )
    return response.json() if response.status_code == 200 else []


def fetch_scan_feedback_enriched(is_resolved: bool = None):
    """Fetch scan feedback with joined scan + user details."""
    params = {}
    if is_resolved is not None:
        params["is_resolved"] = str(is_resolved).lower()
    response = requests.get(
        f"{BACKEND_URL}/api/scan-feedback/enriched/",
        params=params,
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.json() if response.status_code == 200 else []


def resolve_scan_feedback(feedback_id: int):
    """Mark a scan feedback entry as resolved."""
    response = requests.put(
        f"{BACKEND_URL}/api/scan-feedback/{feedback_id}",
        json={"IsResolved": True},
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200


def update_scan_status(scan_id: int, new_status: str):
    """Update the StatusIndicator of a scan record."""
    response = requests.put(
        f"{BACKEND_URL}/api/scans/{scan_id}",
        json={"StatusIndicator": new_status},
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200


def fetch_threat_stats():
    """Return per-country threat counts aggregated from ScanHistory."""
    response = requests.get(
        f"{BACKEND_URL}/api/scans/stats/threats",
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.json() if response.status_code == 200 else []


def fetch_recent_threats():
    """Return the last 20 defanged MALICIOUS/SUSPICIOUS scan records."""
    response = requests.get(
        f"{BACKEND_URL}/api/scans/stats/recent-threats",
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.json() if response.status_code == 200 else []
