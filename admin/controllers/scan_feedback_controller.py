import streamlit as st
from models import api_client


############################################
# This function is to retrieve enriched scan feedback from the backend,
# optionally filtered by resolution status.
############################################
def get_enriched_feedback(is_resolved=None) -> list:
    return api_client.fetch_scan_feedback_enriched(is_resolved)


############################################
# This function is to confirm the current scan verdict, mark the
# feedback as resolved, and log the action.
############################################
def handle_confirm_verdict(feedback_id: int, scan_id: int, current_status: str, current_user_id: int):
    api_client.resolve_scan_feedback(feedback_id)
    api_client.log_action(
        current_user_id, "CONFIRMED_SCAN_VERDICT",
        f"Confirmed Scan #{scan_id} verdict as {current_status} (Feedback #{feedback_id}).",
    )
    st.success(f"Verdict kept as **{current_status}**. Feedback resolved.")
    st.rerun()


############################################
# This function is to update the scan verdict to a new status, resolve
# the feedback, log the action, and rerun. Returns False if the update fails.
############################################
def handle_update_verdict(feedback_id: int, scan_id: int, current_status: str, new_status: str, current_user_id: int) -> bool:
    success = api_client.update_scan_status(scan_id, new_status)
    if success:
        api_client.resolve_scan_feedback(feedback_id)
        api_client.log_action(
            current_user_id, "UPDATED_SCAN_VERDICT",
            f"Changed Scan #{scan_id} verdict from {current_status} to {new_status} (Feedback #{feedback_id}).",
        )
        st.success(f"Scan #{scan_id} updated to **{new_status}** and feedback resolved.")
        st.rerun()
    return success


############################################
# This function is to mark a scan feedback entry as resolved and rerun
# the page to reflect the updated state.
############################################
def handle_resolve(feedback_id: int):
    success = api_client.resolve_scan_feedback(feedback_id)
    if success:
        st.success(f"Feedback #{feedback_id} marked as resolved!")
        st.rerun()
    else:
        st.error(f"Failed to resolve feedback #{feedback_id}.")
