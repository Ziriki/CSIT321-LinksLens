import pandas as pd
import streamlit as st
from models import api_client

def get_users_dataframe():
    """Return all user accounts as a display-ready DataFrame."""
    raw_data = api_client.fetch_all_users()
    if not raw_data: return pd.DataFrame()
    return pd.DataFrame(raw_data)[["UserID", "FullName", "EmailAddress", "RoleID", "IsActive"]]

def handle_deactivation(user_id):
    """Deactivate a user account and refresh the page."""
    if api_client.deactivate_user(user_id):
        st.success(f"User {user_id} deactivated.")
        st.rerun()

def handle_role_update(user_id: int, new_role_id: int):
    """Update a user's role and refresh the page."""
    success = api_client.update_user_details(user_id, {"RoleID": new_role_id})
    if success:
        st.success(f"User {user_id} role updated successfully!")
        st.rerun()
    else:
        st.error("Failed to update user role.")