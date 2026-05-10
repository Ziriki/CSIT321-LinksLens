import streamlit as st
from controllers import auth_controller, feedback_controller
from utils import search_dataframe, render_pagination

auth_controller.require_role(1)

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
