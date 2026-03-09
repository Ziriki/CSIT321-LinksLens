import streamlit as st
from controllers import auth_controller, rules_controller

st.set_page_config(page_title="URL Rules", layout="wide")
# Admin + Moderator (RoleID 1, 2)
auth_controller.require_role(1, 2)
auth_controller.render_sidebar()

st.title("Master URL Rules")
st.markdown("View the global Blacklist and Whitelist active in the system.")

df = rules_controller.get_rules_dataframe()
if df.empty:
    st.info("The master list is currently empty.")
else:
    list_type = st.radio("Filter List Type", ["All", "Blacklist", "Whitelist"], horizontal=True)
    filter_map = {"Blacklist": "BLACKLIST", "Whitelist": "WHITELIST"}
    if list_type != "All":
        df = df[df["ListType"] == filter_map[list_type]]
    st.dataframe(df, use_container_width=True, hide_index=True)
