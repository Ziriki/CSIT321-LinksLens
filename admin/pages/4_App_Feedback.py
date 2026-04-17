import streamlit as st
from controllers import auth_controller, feedback_controller
from config import LOGO_PATH, PAGE_LAYOUT
from utils import search_dataframe, render_pagination

st.set_page_config(page_title="App Feedback", page_icon=LOGO_PATH, layout=PAGE_LAYOUT)
auth_controller.require_role(1)
auth_controller.render_sidebar()

st.title("App Feedback")

PAGE_SIZE = 20

df = feedback_controller.get_feedback_dataframe()
if df.empty:
    st.info("No feedback submitted yet.")
    st.stop()

df = df.sort_values(by="FeedbackID", ascending=False).reset_index(drop=True)

search_query = st.text_input("Search", placeholder="Search by name, feedback content...")
df = search_dataframe(df, search_query)

start, end = render_pagination("feedback_page", len(df), PAGE_SIZE)
st.dataframe(df.iloc[start:end], use_container_width=True, hide_index=True)
