def authenticate_user(email, password):
    response = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"EmailAddress": email, "Password": password, "ClientType": "mobile"}
    )
    return response

def check_backend_health():
    return requests.get(f"{BACKEND_URL}/", headers=_get_headers())

def fetch_pending_requests():
    response = requests.get(f"{BACKEND_URL}/api/blacklist-requests/?status=Pending", headers=_get_headers())
    return response.json() if response.status_code == 200 else []

def update_request_status(request_id: int, status: str, moderator_id: int):
    payload = {"Status": status, "ReviewedBy": moderator_id}
    response = requests.put(f"{BACKEND_URL}/api/blacklist-requests/{request_id}", json=payload, headers=_get_headers())
    return response.status_code == 200

def fetch_all_users():
    response = requests.get(f"{BACKEND_URL}/api/users/", headers=_get_headers())
    return response.json() if response.status_code == 200 else []

def deactivate_user(user_id: int):
    # Sends a PUT request to update the user's IsActive status to False
    response = requests.put(f"{BACKEND_URL}/api/users/{user_id}", json={"IsActive": False}, headers=_get_headers())
    return response.status_code == 200

def fetch_app_feedback():
    response = requests.get(f"{BACKEND_URL}/api/feedback/", headers=_get_headers())
    return response.json() if response.status_code == 200 else []

def fetch_action_history():
    """Fetches the immutable audit log from FastAPI"""
    response = requests.get(f"{BACKEND_URL}/api/history/", headers=_get_headers())
    return response.json() if response.status_code == 200 else []

def update_user_details(user_id: int, payload: dict):
    """Updates any user detail, including roles"""
    response = requests.put(f"{BACKEND_URL}/api/users/{user_id}", json=payload, headers=_get_headers())
    return response.status_code == 200

def fetch_url_rules():
    """Fetches the global Blacklist and Whitelist"""
    response = requests.get(f"{BACKEND_URL}/api/url-rules/", headers=_get_headers())
    return response.json() if response.status_code == 200 else []

def fetch_scan_details(scan_id: int):
    """Fetches a specific scan's deep forensic data"""
    response = requests.get(f"{BACKEND_URL}/api/scans/{scan_id}", headers=_get_headers())
    return response.json() if response.status_code == 200 else None