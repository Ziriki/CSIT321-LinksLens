import pandas as pd
from models import api_client
import streamlit as st

def get_pending_requests_dataframe():
    raw_data = api_client.fetch_pending_requests()
    if not raw_data: return pd.DataFrame()
    return pd.DataFrame(raw_data)[["RequestID", "URLDomain", "UserID", "CreatedAt"]]

def handle_review_action(request_id, action):
    success = api_client.update_request_status(request_id, action, moderator_id=1)
    if success:
        st.success(f"Request {action}!")
        st.rerun()