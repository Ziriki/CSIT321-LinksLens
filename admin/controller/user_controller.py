import pandas as pd
import streamlit as st
from models import api_client

def get_users_dataframe():
    raw_data = api_client.fetch_all_users()
    if not raw_data: return pd.DataFrame()
    return pd.DataFrame(raw_data)[["UserID", "EmailAddress", "RoleID", "IsActive"]]

def handle_deactivation(user_id):
    if api_client.deactivate_user(user_id):
        st.success(f"User {user_id} deactivated.")
        st.rerun()