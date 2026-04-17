import pandas as pd
import streamlit as st
from models import api_client


def get_scan_feedback_dataframe(is_resolved: bool = None):
    """Return scan feedback as a display-ready DataFrame, optionally filtered by resolution status."""
    raw_data = api_client.fetch_scan_feedback(is_resolved)
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)

    df.rename(columns={"FullName": "User"}, inplace=True)

    cols = ["FeedbackID", "ScanID", "User", "SuggestedStatus", "Comments", "IsResolved"]
    available = [c for c in cols if c in df.columns]
    return df[available]


def handle_resolve(feedback_id: int):
    """Mark a scan feedback entry as resolved and refresh the page."""
    success = api_client.resolve_scan_feedback(feedback_id)
    if success:
        st.success(f"Feedback #{feedback_id} marked as resolved!")
        st.rerun()
    else:
        st.error(f"Failed to resolve feedback #{feedback_id}.")
