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