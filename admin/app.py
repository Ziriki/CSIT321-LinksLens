import streamlit as st
import requests
import pandas as pd
import time

# Use the internal docker network name to talk to backend
BACKEND_URL = "http://backend:8000"

st.set_page_config(page_title="LinkLens Admin", layout="wide")

st.title("🛡️ LinkLens Admin Dashboard")
st.markdown("Monitor incoming scan requests and system health.")

# Sidebar for navigation
st.sidebar.header("Navigation")
menu = st.sidebar.radio("Go to", ["Live Dashboard", "Database Viewer", "System Health"])

if menu == "Live Dashboard":
    # Top Stats Row
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Scans Today", "1,240", "+12%")
    col2.metric("Phishing Detected", "45", "-2%")
    col3.metric("Active Users", "18", "Online")

    st.subheader("Recent Scan Requests")
    # Fake data table for now
    data = {
        'Timestamp': ['10:01 AM', '10:05 AM', '10:12 AM'],
        'URL': ['google.com', 'secure-bank-login-update.com', 'shopee.sg'],
        'Verdict': ['SAFE', 'DANGEROUS', 'SAFE'],
        'Confidence': ['99%', '85%', '98%']
    }
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

elif menu == "System Health":
    st.subheader("Backend Connection Status")
    
    if st.button("Check Backend API"):
        try:
            # We talk to the backend container directly!
            response = requests.get(f"{BACKEND_URL}/")
            if response.status_code == 200:
                st.success(f"Backend is Online! Message: {response.json()}")
            else:
                st.error("Backend returned an error.")
        except Exception as e:
            st.error(f"Failed to connect to backend: {e}")

elif menu == "Database Viewer":
    st.info("Database connection not yet configured. (Waiting for MySQL credentials)")