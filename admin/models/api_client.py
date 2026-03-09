import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")


def _get_headers():
    """Attach the JWT Bearer token from session state to every API call."""
    token = st.session_state.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


# -- Auth --

def authenticate_user(email: str, password: str):
    """Login via mobile client type so we get the JWT in the response body."""
    return requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"EmailAddress": email, "Password": password, "ClientType": "mobile"},
    )


# -- System Health --

def check_backend_health():
    return requests.get(f"{BACKEND_URL}/", headers=_get_headers())


def fetch_system_health():
    """Fetches detailed system health stats (admin only)."""
    response = requests.get(f"{BACKEND_URL}/api/health", headers=_get_headers())
    return response.json() if response.status_code == 200 else None


# -- Blacklist Requests (Moderation) --

def fetch_pending_requests():
    response = requests.get(
        f"{BACKEND_URL}/api/blacklist-requests/?status=PENDING", headers=_get_headers()
    )
    return response.json() if response.status_code == 200 else []


def update_request_status(request_id: int, status: str, moderator_id: int):
    payload = {"Status": status, "ReviewedBy": moderator_id}
    response = requests.put(
        f"{BACKEND_URL}/api/blacklist-requests/{request_id}",
        json=payload,
        headers=_get_headers(),
    )
    return response.status_code == 200


# -- User Accounts --

def fetch_all_users():
    response = requests.get(f"{BACKEND_URL}/api/accounts/", headers=_get_headers())
    return response.json() if response.status_code == 200 else []


def deactivate_user(user_id: int):
    response = requests.put(
        f"{BACKEND_URL}/api/accounts/{user_id}",
        json={"IsActive": False},
        headers=_get_headers(),
    )
    return response.status_code == 200


def update_user_details(user_id: int, payload: dict):
    response = requests.put(
        f"{BACKEND_URL}/api/accounts/{user_id}",
        json=payload,
        headers=_get_headers(),
    )
    return response.status_code == 200


# -- User Details --

def fetch_user_detail(user_id: int):
    response = requests.get(
        f"{BACKEND_URL}/api/details/{user_id}", headers=_get_headers()
    )
    return response.json() if response.status_code == 200 else None


def update_user_profile(user_id: int, payload: dict):
    """Update user details (FullName, PhoneNumber, Address, Gender, DateOfBirth)."""
    response = requests.put(
        f"{BACKEND_URL}/api/details/{user_id}",
        json=payload,
        headers=_get_headers(),
    )
    return response.status_code == 200


# -- App Feedback --

def fetch_app_feedback():
    response = requests.get(f"{BACKEND_URL}/api/feedback/", headers=_get_headers())
    return response.json() if response.status_code == 200 else []


# -- Action History --

def fetch_action_history():
    response = requests.get(f"{BACKEND_URL}/api/history/", headers=_get_headers())
    return response.json() if response.status_code == 200 else []


# -- URL Rules --

def fetch_url_rules():
    response = requests.get(f"{BACKEND_URL}/api/url-rules/", headers=_get_headers())
    return response.json() if response.status_code == 200 else []


# -- Scan History --

def fetch_scan_list(skip: int = 0, limit: int = 25, search_url: str = None,
                    status_indicator: str = None, user_id: int = None):
    """Fetch paginated scan history with optional filters."""
    params = {"skip": skip, "limit": limit}
    if search_url:
        params["search_url"] = search_url
    if status_indicator:
        params["status_indicator"] = status_indicator
    if user_id:
        params["user_id"] = user_id
    response = requests.get(
        f"{BACKEND_URL}/api/scans/", params=params, headers=_get_headers()
    )
    return response.json() if response.status_code == 200 else []


def fetch_scan_details(scan_id: int):
    response = requests.get(
        f"{BACKEND_URL}/api/scans/{scan_id}", headers=_get_headers()
    )
    return response.json() if response.status_code == 200 else None


# -- Scan Feedback --

def fetch_scan_feedback(is_resolved: bool = None):
    params = {}
    if is_resolved is not None:
        params["is_resolved"] = str(is_resolved).lower()
    response = requests.get(
        f"{BACKEND_URL}/api/scan-feedback/", params=params, headers=_get_headers()
    )
    return response.json() if response.status_code == 200 else []


def fetch_scan_feedback_enriched(is_resolved: bool = None):
    """Fetch scan feedback with joined scan + user details."""
    params = {}
    if is_resolved is not None:
        params["is_resolved"] = str(is_resolved).lower()
    response = requests.get(
        f"{BACKEND_URL}/api/scan-feedback/enriched/", params=params, headers=_get_headers()
    )
    return response.json() if response.status_code == 200 else []


def resolve_scan_feedback(feedback_id: int):
    response = requests.put(
        f"{BACKEND_URL}/api/scan-feedback/{feedback_id}",
        json={"IsResolved": True},
        headers=_get_headers(),
    )
    return response.status_code == 200


def update_scan_status(scan_id: int, new_status: str):
    """Update the StatusIndicator of a scan record."""
    response = requests.put(
        f"{BACKEND_URL}/api/scans/{scan_id}",
        json={"StatusIndicator": new_status},
        headers=_get_headers(),
    )
    return response.status_code == 200
