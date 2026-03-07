import streamlit as st
from controllers import auth_controller, rules_controller

st.set_page_config(page_title="URL Rules", layout="wide")
# Moderator + Admin (RoleID 2, 3)
auth_controller.require_role(2, 3)

st.title("Master URL Rules")
st.markdown("View the global Blacklist and Whitelist active in the system.")

df = rules_controller.get_rules_dataframe()
if df.empty:
    st.info("The master list is currently empty.")
else:
    list_type = st.radio("Filter List Type", ["All", "Blacklist", "Whitelist"], horizontal=True)
    if list_type != "All":
        df = df[df["ListType"] == list_type]
    st.dataframe(df, use_container_width=True, hide_index=True)
