import streamlit as st
from controllers import auth_controller, action_history_controller
from utils import search_dataframe, render_pagination

auth_controller.require_role(1)

st.title("Action History Log")
st.markdown("Immutable record of all moderator and admin actions.")

PAGE_SIZE = 20

df = action_history_controller.get_audit_dataframe()
if df.empty:
    st.info("No action history logs found.")
    st.stop()

df = df.reset_index(drop=True)

search_query = st.text_input("Search", placeholder="Search by name, action type, action...")
df = search_dataframe(df, search_query)

start, end = render_pagination("history_page", len(df), PAGE_SIZE)
st.dataframe(df.iloc[start:end], use_container_width=True, hide_index=True)
