import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

_TIMEOUT = 10  # seconds, default timeout for all API calls


############################################
# This function is to build the Authorization header using the JWT
# stored in session state, required for all authenticated API calls.
############################################
def _get_headers():
    token = st.session_state.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


# -- Auth --

############################################
# This function is to send the login credentials to the backend and
# return the raw response object for the caller to inspect.
############################################
def authenticate_user(email: str, password: str):
    return requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"EmailAddress": email, "Password": password, "ClientType": "web"},
        timeout=_TIMEOUT,
    )


# -- System Health --

############################################
# This function is to ping the backend root endpoint and return the
# raw response for health checking.
############################################
def check_backend_health():
    return requests.get(f"{BACKEND_URL}/", headers=_get_headers(), timeout=_TIMEOUT)


############################################
# This function is to fetch detailed system health stats from the
# admin health endpoint, including component status and pending work.
############################################
def fetch_system_health():
    response = requests.get(f"{BACKEND_URL}/api/health", headers=_get_headers(), timeout=_TIMEOUT)
    return response.json() if response.status_code == 200 else None  # 200 = OK


# -- User Accounts --

############################################
# This function is to retrieve all user accounts from the backend.
############################################
def fetch_all_users():
    response = requests.get(f"{BACKEND_URL}/api/accounts/", params={"limit": 10000}, headers=_get_headers(), timeout=_TIMEOUT)
    return response.json() if response.status_code == 200 else []  # 200 = OK


############################################
# This function is to set a user account to inactive (soft delete).
############################################
def deactivate_user(user_id: int):
    response = requests.put(
        f"{BACKEND_URL}/api/accounts/{user_id}",
        json={"IsActive": False},
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200  # 200 = OK


############################################
# This function is to restore a previously deactivated user account
# by setting it back to active.
############################################
def activate_user(user_id: int):
    response = requests.put(
        f"{BACKEND_URL}/api/accounts/{user_id}",
        json={"IsActive": True},
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200  # 200 = OK


############################################
# This function is to update account-level fields (e.g. EmailAddress,
# RoleID, IsActive) for a given user.
############################################
def update_user_details(user_id: int, payload: dict):
    response = requests.put(
        f"{BACKEND_URL}/api/accounts/{user_id}",
        json=payload,
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200  # 200 = OK


# -- User Details --

############################################
# This function is to retrieve profile details (name, phone, address,
# etc.) for a single user, or return None if not found.
############################################
def fetch_user_detail(user_id: int):
    response = requests.get(
        f"{BACKEND_URL}/api/details/{user_id}", headers=_get_headers(), timeout=_TIMEOUT
    )
    return response.json() if response.status_code == 200 else None  # 200 = OK


############################################
# This function is to update profile details (FullName, PhoneNumber,
# Address, Gender, DateOfBirth) for a given user.
############################################
def update_user_profile(user_id: int, payload: dict):
    response = requests.put(
        f"{BACKEND_URL}/api/details/{user_id}",
        json=payload,
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200  # 200 = OK


# -- App Feedback --

############################################
# This function is to retrieve all app feedback submissions from users.
############################################
def fetch_app_feedback():
    response = requests.get(f"{BACKEND_URL}/api/feedback/", headers=_get_headers(), timeout=_TIMEOUT)
    return response.json() if response.status_code == 200 else []  # 200 = OK


# -- Action History --

############################################
# This function is to retrieve all audit log entries from the backend.
############################################
def fetch_action_history():
    response = requests.get(f"{BACKEND_URL}/api/history/", headers=_get_headers(), timeout=_TIMEOUT)
    return response.json() if response.status_code == 200 else []  # 200 = OK


############################################
# This function is to log an action to the audit trail. Silently ignores
# failures — logging is non-critical and should not interrupt the user.
############################################
def log_action(user_id: int, action_type: str, action: str):
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

############################################
# This function is to retrieve all URL blacklist and whitelist rules.
############################################
def fetch_url_rules():
    response = requests.get(f"{BACKEND_URL}/api/url-rules/", params={"limit": 10000}, headers=_get_headers(), timeout=_TIMEOUT)
    return response.json() if response.status_code == 200 else []  # 200 = OK


############################################
# This function is to add a domain to the blacklist or whitelist.
############################################
def create_url_rule(domain: str, list_type: str, added_by: int):
    response = requests.post(
        f"{BACKEND_URL}/api/url-rules/",
        json={"URLDomain": domain, "ListType": list_type, "AddedBy": added_by},
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 201  # 201 = Created


############################################
# This function is to delete a URL rule by its ID.
############################################
def delete_url_rule(rule_id: int):
    response = requests.delete(
        f"{BACKEND_URL}/api/url-rules/{rule_id}", headers=_get_headers(), timeout=_TIMEOUT
    )
    return response.status_code == 204  # 204 = No Content (successful delete)


# -- Scan History --

############################################
# This function is to submit a URL to the scan pipeline and return the
# result dict, or None on failure. Timeout is 120 s — the scan pipeline
# can take up to ~90 s.
############################################
def scan_url(url: str) -> dict | None:
    try:
        response = requests.post(
            f"{BACKEND_URL}/scan",
            json={"urls": url},
            headers=_get_headers(),
            timeout=120,  # 120s to accommodate the ~90s scan pipeline
        )
        if response.status_code == 200:  # 200 = OK
            results = response.json()
            return results[0] if results else None
    except Exception:
        pass
    return None


############################################
# This function is to fetch a paginated list of scan records with
# optional filters for search keyword, status indicator, and user ID.
############################################
def fetch_scan_list(skip: int = 0, limit: int = 25, search: str = None,
                    status_indicator: str = None, user_id: int = None):
    params = {"skip": skip, "limit": limit}
    if search:
        params["search"] = search
    if status_indicator:
        # status_indicator values: SAFE, SUSPICIOUS, MALICIOUS, UNAVAILABLE, PENDING
        params["status_indicator"] = status_indicator
    if user_id:
        params["user_id"] = user_id
    response = requests.get(
        f"{BACKEND_URL}/api/scans/", params=params, headers=_get_headers(), timeout=_TIMEOUT
    )
    return response.json() if response.status_code == 200 else []  # 200 = OK


############################################
# This function is to retrieve the full details for a single scan
# record by its ID.
############################################
def fetch_scan_details(scan_id: int):
    response = requests.get(
        f"{BACKEND_URL}/api/scans/{scan_id}", headers=_get_headers(), timeout=_TIMEOUT
    )
    return response.json() if response.status_code == 200 else None  # 200 = OK


# -- Scan Feedback --

############################################
# This function is to retrieve scan feedback submissions, optionally
# filtered by whether they have been resolved.
############################################
def fetch_scan_feedback(is_resolved: bool = None):
    params = {}
    if is_resolved is not None:
        params["is_resolved"] = str(is_resolved).lower()
    response = requests.get(
        f"{BACKEND_URL}/api/scan-feedback/", params=params, headers=_get_headers(), timeout=_TIMEOUT
    )
    return response.json() if response.status_code == 200 else []  # 200 = OK


############################################
# This function is to retrieve enriched scan feedback that includes
# joined scan details and user information in a single response.
############################################
def fetch_scan_feedback_enriched(is_resolved: bool = None):
    params = {}
    if is_resolved is not None:
        params["is_resolved"] = str(is_resolved).lower()
    response = requests.get(
        f"{BACKEND_URL}/api/scan-feedback/enriched/",
        params=params,
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.json() if response.status_code == 200 else []  # 200 = OK


############################################
# This function is to mark a scan feedback entry as resolved.
############################################
def resolve_scan_feedback(feedback_id: int):
    response = requests.put(
        f"{BACKEND_URL}/api/scan-feedback/{feedback_id}",
        json={"IsResolved": True},
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200  # 200 = OK


############################################
# This function is to update the status indicator of a scan record.
# Accepted values: SAFE, SUSPICIOUS, MALICIOUS, UNAVAILABLE
############################################
def update_scan_status(scan_id: int, new_status: str):
    response = requests.put(
        f"{BACKEND_URL}/api/scans/{scan_id}",
        json={"StatusIndicator": new_status},
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.status_code == 200  # 200 = OK


############################################
# This function is to retrieve per-country threat counts aggregated
# from all MALICIOUS and SUSPICIOUS scan records.
############################################
def fetch_threat_stats():
    response = requests.get(
        f"{BACKEND_URL}/api/scans/stats/threats",
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.json() if response.status_code == 200 else []  # 200 = OK


############################################
# This function is to retrieve the most recent MALICIOUS and SUSPICIOUS
# scans. URLs are defanged (hxxps://) by the backend before returning.
############################################
def fetch_recent_threats():
    response = requests.get(
        f"{BACKEND_URL}/api/scans/stats/recent-threats",
        headers=_get_headers(),
        timeout=_TIMEOUT,
    )
    return response.json() if response.status_code == 200 else []  # 200 = OK
