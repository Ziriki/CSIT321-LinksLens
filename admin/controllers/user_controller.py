import pandas as pd
import streamlit as st
from models import api_client

_ACCOUNT_FIELDS = ("EmailAddress", "RoleID")


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
# This function is to retrieve the full detail record for a single user.
############################################
def get_user_detail(user_id: int) -> dict:
    return api_client.fetch_user_detail(user_id) or {}


############################################
# This function is to apply a snapshot of changed fields to a user
# account and profile, log the action, clear the data cache, and rerun.
############################################
def handle_update(user_id: int, snapshot: dict, current_user_id: int):
    account_payload = {k: v for k, v in snapshot.items() if k in _ACCOUNT_FIELDS}
    detail_payload = {k: v for k, v in snapshot.items() if k not in _ACCOUNT_FIELDS}
    if account_payload:
        api_client.update_user_details(user_id, account_payload)
    if detail_payload:
        api_client.update_user_profile(user_id, detail_payload)
    changes = ", ".join(f"{k}={v}" for k, v in snapshot.items())
    api_client.log_action(current_user_id, "UPDATED_USER", f"Updated User #{user_id}: {changes}.")
    st.cache_data.clear()
    st.rerun()


############################################
# This function is to activate or deactivate a user account, log the
# action, clear the data cache, and rerun.
############################################
def handle_status_toggle(user_id: int, action: str, current_user_id: int):
    if action == "deactivate":
        api_client.deactivate_user(user_id)
        api_client.log_action(current_user_id, "DEACTIVATED_USER", f"Deactivated User #{user_id}.")
    else:
        api_client.activate_user(user_id)
        api_client.log_action(current_user_id, "ACTIVATED_USER", f"Activated User #{user_id}.")
    st.cache_data.clear()
    st.rerun()
