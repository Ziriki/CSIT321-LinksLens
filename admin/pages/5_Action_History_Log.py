# pages/5_Audit_Log.py
import streamlit as st
from controllers import auth_controller, audit_controller

st.set_page_config(page_title="System Audit Log", layout="wide")
auth_controller.require_auth()

st.title("System Audit Log")
st.markdown("Immutable record of all moderator and admin actions.")

df = audit_controller.get_audit_dataframe()
if df.empty:
    st.info("No audit logs found.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)