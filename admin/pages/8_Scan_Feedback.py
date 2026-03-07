import streamlit as st
from controllers import auth_controller, scan_feedback_controller

st.set_page_config(page_title="Scan Feedback", layout="wide")
# Moderator + Admin (RoleID 2, 3)
auth_controller.require_role(2, 3)

st.title("Scan Feedback Review")
st.markdown("Review user-submitted feedback on scan results and mark as resolved.")

filter_option = st.radio("Filter", ["Unresolved", "Resolved", "All"], horizontal=True)
is_resolved = {"Unresolved": False, "Resolved": True, "All": None}[filter_option]

df = scan_feedback_controller.get_scan_feedback_dataframe(is_resolved)
if df.empty:
    st.info("No scan feedback found.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("### Resolve Feedback")
    feedback_id = st.number_input("Feedback ID to resolve", min_value=1, step=1)
    if st.button("Mark as Resolved"):
        scan_feedback_controller.handle_resolve(feedback_id)
