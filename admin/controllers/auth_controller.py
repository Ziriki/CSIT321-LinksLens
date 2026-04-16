import time

import jwt
import streamlit as st
from models import api_client

ROLE_LABELS = {1: "Administrator", 2: "Moderator", 3: "User"}


def _decode_token():
    """Decode the stored JWT to extract user_id and role_id (cached per rerun)."""
    if "_decoded_user" in st.session_state:
        return st.session_state["_decoded_user"]
    token = st.session_state.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        user = {"user_id": int(payload["sub"]), "role_id": int(payload["role"])}
        st.session_state["_decoded_user"] = user
        return user
    except Exception:
        return None


def require_auth():
    """Redirect unauthenticated or expired-session users back to the login page."""
    token = st.session_state.get("access_token")
    if not token:
        st.error("Please log in first.")
        st.stop()
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        if payload.get("exp", 0) < time.time():
            st.session_state["access_token"] = None
            st.session_state.pop("_decoded_user", None)
            st.session_state["session_expired"] = True
            st.switch_page("app.py")
    except Exception:
        st.session_state["access_token"] = None
        st.session_state.pop("_decoded_user", None)
        st.session_state["session_expired"] = True
        st.switch_page("app.py")


# Streamlit uses the page filename as the sidebar link href — match on filename substrings.
_MODERATOR_HIDDEN_PAGES = ["1_Dashboard", "3_User_Management", "4_App_Feedback", "5_Action_History_Log"]


def _hide_pages_for_moderator():
    """Inject CSS to hide admin-only pages from the moderator sidebar."""
    user = _decode_token()
    if user and user["role_id"] == 2:
        css_selectors = ", ".join(
            f'[data-testid="stSidebarNav"] a[href*="{name}"]'
            for name in _MODERATOR_HIDDEN_PAGES
        )
        st.markdown(
            f"""
            <style>
                {css_selectors} {{
                    display: none !important;
                }}
            </style>
            """,
            unsafe_allow_html=True,
        )


def require_role(*allowed_roles: int):
    """Block users whose role is not in the allowed list."""
    require_auth()
    user = _decode_token()
    _hide_pages_for_moderator()
    if not user or user["role_id"] not in allowed_roles:
        st.error("You do not have permission to view this page.")
        st.stop()
    return user


def get_current_user():
    """Return the current user's decoded token data, or None."""
    return _decode_token()


def render_sidebar():
    """Show role label and logout button in the sidebar."""
    _hide_pages_for_moderator()
    user = _decode_token()
    if user:
        role_label = ROLE_LABELS.get(user["role_id"], "Unknown")
        st.sidebar.write(f"Logged in as **{role_label}**")

    st.sidebar.markdown("---")

    if not st.session_state.get("confirm_logout"):
        if st.sidebar.button("Log Out"):
            st.session_state["confirm_logout"] = True
            st.rerun()
    else:
        st.sidebar.warning("Are you sure you want to log out?")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Yes", key="confirm_logout_yes"):
                if user:
                    api_client.log_action(user["user_id"], "LOGOUT", "Logged out of admin portal.")
                st.session_state["access_token"] = None
                st.session_state.pop("_decoded_user", None)
                st.session_state.pop("confirm_logout", None)
                st.switch_page("app.py")
        with col2:
            if st.button("No", key="confirm_logout_no"):
                st.session_state.pop("confirm_logout", None)
                st.rerun()


def handle_login(email, password):
    if not email or not password:
        st.error("Please fill in both fields.")
        return
    # Clear any stale decoded-user cache so the new token is always decoded fresh
    st.session_state.pop("_decoded_user", None)
    with st.spinner("Authenticating..."):
        response = api_client.authenticate_user(email, password)
        if response.status_code == 200:
            data = response.json()
            token = data["access_token"]
            # Block regular users (RoleID 3) from accessing the admin portal
            try:
                payload = jwt.decode(token, options={"verify_signature": False})
                role_id = int(payload.get("role", 0))
                if role_id not in (1, 2):  # Only Administrator (1) and Moderator (2)
                    st.error("Login failed. Check credentials.")
                    return
            except Exception:
                st.error("Login failed. Check credentials.")
                return
            st.session_state["access_token"] = token
            user_info = _decode_token()
            if user_info:
                api_client.log_action(user_info["user_id"], "LOGIN", "Logged in to admin portal.")
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Login failed. Check credentials.")
