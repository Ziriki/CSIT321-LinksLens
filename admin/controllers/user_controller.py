import pandas as pd
import streamlit as st
from models import api_client


############################################
# This function is to retrieve all user accounts from the backend and
# return them as a display-ready DataFrame with key columns only.
############################################
def get_users_dataframe():
    raw_data = api_client.fetch_all_users()
    if not raw_data:
        return pd.DataFrame()
    return pd.DataFrame(raw_data)[["UserID", "FullName", "EmailAddress", "RoleID", "IsActive"]]


############################################
# This function is to deactivate a user account and rerun the page to
# reflect the updated status.
############################################
def handle_deactivation(user_id):
    if api_client.deactivate_user(user_id):
        st.success(f"User {user_id} deactivated.")
        st.rerun()


############################################
# This function is to update the role of a user account and rerun the
# page to reflect the change.
# Role IDs: 1 = Administrator, 2 = Moderator, 3 = User
############################################
def handle_role_update(user_id: int, new_role_id: int):
    success = api_client.update_user_details(user_id, {"RoleID": new_role_id})
    if success:
        st.success(f"User {user_id} role updated successfully!")
        st.rerun()
    else:
        st.error("Failed to update user role.")
