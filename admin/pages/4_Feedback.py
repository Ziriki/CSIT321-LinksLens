import streamlit as st
from controllers import auth_controller, feedback_controller

st.set_page_config(page_title="App Feedback", layout="wide")
# Admin only (RoleID 3)
auth_controller.require_role(3)

st.title("App Feedback")
df = feedback_controller.get_feedback_dataframe()
if df.empty:
    st.info("No feedback submitted yet.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)
