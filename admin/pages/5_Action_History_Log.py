import streamlit as st
from controllers import auth_controller, action_history_controller

st.set_page_config(page_title="Action History Log", layout="wide")
# Admin only (RoleID 1)
auth_controller.require_role(1)
auth_controller.render_sidebar()

st.title("Action History Log")
st.markdown("Immutable record of all moderator and admin actions.")

df = action_history_controller.get_audit_dataframe()
if df.empty:
    st.info("No action history logs found.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)
