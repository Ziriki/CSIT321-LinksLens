import streamlit as st
from controllers import moderation_controller

st.title("Moderation Queue")
df = moderation_controller.get_pending_requests_dataframe()
st.dataframe(df)

target_id = st.number_input("Request ID", min_value=1)
if st.button("Approve"):
    moderation_controller.handle_review_action(target_id, "Approved")
if st.button("Reject"):
    moderation_controller.handle_review_action(target_id, "Rejected")