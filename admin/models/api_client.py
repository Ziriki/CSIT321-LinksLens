def authenticate_user(email, password):
    response = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"EmailAddress": email, "Password": password, "ClientType": "mobile"}
    )
    return response