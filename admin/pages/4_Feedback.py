import streamlit as st
from controllers import feedback_controller

st.title("App Feedback")
df = feedback_controller.get_feedback_dataframe()
st.dataframe(df)