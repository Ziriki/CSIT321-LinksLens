import streamlit as st
from models import api_client

st.title("System Health")
if st.button("Check API Status"):
    response = api_client.check_backend_health()
    if response.status_code == 200:
        st.success("Backend is Online and Healthy!")
    else:
        st.error("Backend is down or unreachable.")