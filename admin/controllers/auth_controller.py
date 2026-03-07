import jwt
import streamlit as st
from models import api_client


def _decode_token():
    """Decode the stored JWT to extract user_id and role_id."""
    token = st.session_state.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return {"user_id": int(payload["sub"]), "role_id": int(payload["role"])}
    except Exception:
        return None


def require_auth():
    """Redirect unauthenticated users back to the login page."""
    if not st.session_state.get("access_token"):
        st.error("Please log in first.")
        st.stop()


def require_role(*allowed_roles: int):
    """Block users whose role is not in the allowed list."""
    require_auth()
    user = _decode_token()
    if not user or user["role_id"] not in allowed_roles:
        st.error("You do not have permission to view this page.")
        st.stop()
    return user


def get_current_user():
    """Return the current user's decoded token data, or None."""
    return _decode_token()


def handle_login(email, password):
    if not email or not password:
        st.error("Please fill in both fields.")
        return
    with st.spinner("Authenticating..."):
        response = api_client.authenticate_user(email, password)
        if response.status_code == 200:
            data = response.json()
            st.session_state["access_token"] = data["access_token"]
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Login failed. Check credentials.")
