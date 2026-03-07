def authenticate_user(email, password):
    response = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"EmailAddress": email, "Password": password, "ClientType": "mobile"}
    )
    return response

def check_backend_health():
    return requests.get(f"{BACKEND_URL}/", headers=_get_headers())