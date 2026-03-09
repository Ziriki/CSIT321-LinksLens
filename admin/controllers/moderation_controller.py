import pandas as pd
import streamlit as st
from models import api_client


def get_pending_requests_dataframe():
    raw_data = api_client.fetch_pending_requests()
    if not raw_data:
        return pd.DataFrame()
    return pd.DataFrame(raw_data)[["RequestID", "URLDomain", "UserID", "CreatedAt"]]


def handle_review_action(request_id, action, moderator_id):
    success = api_client.update_request_status(request_id, action, moderator_id)
    if success:
        api_client.log_action(
            moderator_id,
            f"{action.upper()}_BLACKLIST",
            f"{action} blacklist request #{request_id}.",
        )
        st.success(f"Request {request_id} {action}!")
        st.rerun()
    else:
        st.error(f"Failed to update request {request_id}.")
