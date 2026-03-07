# pages/6_Master_Rules.py
import streamlit as st
from controllers import auth_controller, rules_controller

st.set_page_config(page_title="Master Rules Viewer", layout="wide")
auth_controller.require_auth()

st.title("Master URL Rules")
st.markdown("View the global Blacklist and Whitelist active in the system.")

df = rules_controller.get_rules_dataframe()
if df.empty:
    st.info("The master list is currently empty.")
else:
    # Filter by list type for easy viewing
    list_type = st.radio("Filter List Type", ["All", "Blacklist", "Whitelist"], horizontal=True)
    if list_type != "All":
        df = df[df["ListType"] == list_type]
        
    st.dataframe(df, use_container_width=True, hide_index=True)