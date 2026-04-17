import streamlit as st
from controllers import auth_controller, action_history_controller
from config import LOGO_PATH, PAGE_LAYOUT
from utils import search_dataframe, render_pagination

st.set_page_config(page_title="Action History Log", page_icon=LOGO_PATH, layout=PAGE_LAYOUT)
auth_controller.require_role(1)
auth_controller.render_sidebar()

st.title("Action History Log")
st.markdown("Immutable record of all moderator and admin actions.")

PAGE_SIZE = 20

df = action_history_controller.get_audit_dataframe()
if df.empty:
    st.info("No action history logs found.")
    st.stop()

# Already sorted descending by LogID in controller, reset index
df = df.reset_index(drop=True)

search_query = st.text_input("Search", placeholder="Search by name, action type, action...")
df = search_dataframe(df, search_query)

start, end = render_pagination("history_page", len(df), PAGE_SIZE)
st.dataframe(df.iloc[start:end], use_container_width=True, hide_index=True)
