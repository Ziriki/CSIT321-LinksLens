import os

import jwt
import streamlit as st
from models import api_client

_SECRET_KEY = os.getenv("SECRET_KEY")
if not _SECRET_KEY:
    raise ValueError("FATAL: SECRET_KEY environment variable is not set!")
_ALGORITHM  = os.getenv("ALGORITHM", "HS256")

ROLE_LABELS = {1: "Administrator", 2: "Moderator", 3: "User"}


############################################
# This function is to decode the JWT stored in session state and return
# a dict with user_id and role_id. Result is cached for the current
# rerun to avoid repeated decoding on the same page load.
############################################
def _decode_token():
    if "_decoded_user" in st.session_state:
        return st.session_state["_decoded_user"]
    token = st.session_state.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        user = {"user_id": int(payload["sub"]), "role_id": int(payload["role"])}
        st.session_state["_decoded_user"] = user
        return user
    except Exception:
        return None


############################################
# This function is to clear the auth state and trigger a rerun so the
# user is redirected to the login page with a session-expired flag set.
############################################
def _expire_session():
    st.session_state["access_token"] = None
    st.session_state.pop("_decoded_user", None)
    st.session_state["session_expired"] = True
    st.rerun()


############################################
# This function is to stop page rendering if the user has no valid token
# or if the session has expired, redirecting them back to the login page.
############################################
def require_auth():
    token = st.session_state.get("access_token")
    if not token:
        st.error("Please log in first.")
        st.stop()
    if not _decode_token():
        _expire_session()


# Streamlit uses the page filename as the sidebar link href. Match on filename substrings.
_MODERATOR_HIDDEN_PAGES = ["1_Dashboard", "2_User_Management", "3_App_Feedback", "4_Action_History_Log"]


############################################
# This function is to inject CSS that hides admin-only sidebar links
# from users with the Moderator role.
############################################
def _hide_pages_for_moderator():
    user = _decode_token()
    if user and user["role_id"] == 2:  # 2 = Moderator
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


############################################
# This function is to enforce role-based access control for a page.
# Stops rendering and shows an error if the user's role is not in allowed_roles.
############################################
def require_role(*allowed_roles: int):
    require_auth()
    user = _decode_token()
    _hide_pages_for_moderator()
    if not user or user["role_id"] not in allowed_roles:
        st.error("You do not have permission to view this page.")
        st.stop()
    return user


############################################
# This function is to return the currently logged-in user's decoded
# token data, or None if no valid session exists.
############################################
def get_current_user():
    return _decode_token()


############################################
# This function is to render the role label and logout button in the
# sidebar, including a confirmation step before logging out.
############################################
def render_sidebar():
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
                st.rerun()
        with col2:
            if st.button("No", key="confirm_logout_no"):
                st.session_state.pop("confirm_logout", None)
                st.rerun()


############################################
# This function is to handle the login form submission, authenticate
# the user, validate their role, store the JWT, and log the login action.
############################################
def handle_login(email, password):
    if not email or not password:
        st.error("Please fill in both fields.")
        return
    # Clear any stale decoded-user cache so the new token is always decoded fresh
    st.session_state.pop("_decoded_user", None)
    with st.spinner("Authenticating..."):
        response = api_client.authenticate_user(email, password)
        if response.status_code == 200:  # 200 = OK
            data = response.json()
            token = data["access_token"]
            try:
                payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
                role_id = int(payload.get("role", 0))
                if role_id not in (1, 2):  # 1 = Administrator, 2 = Moderator (all other roles are blocked)
                    st.error("Login failed. Check credentials.")
                    return
            except Exception:
                st.error("Login failed. Check credentials.")
                return
            st.session_state["access_token"] = token
            user_id = int(payload["sub"])
            st.session_state["_decoded_user"] = {"user_id": user_id, "role_id": role_id}
            api_client.log_action(user_id, "LOGIN", "Logged in to admin portal.")
            st.rerun()
        else:
            st.error("Login failed. Check credentials.")
