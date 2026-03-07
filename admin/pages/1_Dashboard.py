import streamlit as st
from controllers import auth_controller
from models import api_client

st.set_page_config(page_title="Dashboard", layout="wide")
# Admin only (RoleID 3)
auth_controller.require_role(3)

st.title("System Dashboard")

# Basic API health check
if st.button("Check API Status"):
    response = api_client.check_backend_health()
    if response.status_code == 200:
        st.success("Backend is Online and Healthy!")
    else:
        st.error("Backend is down or unreachable.")

# Detailed system health stats
st.markdown("---")
st.subheader("System Statistics")
health = api_client.fetch_system_health()
if health:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Database", health["database"])
        st.metric("Total Users", health["total_users"])
    with col2:
        st.metric("Active Users", health["active_users"])
        st.metric("Total Scans", health["total_scans"])
    with col3:
        st.metric("Pending Blacklist Requests", health["pending_blacklist_requests"])
        st.metric("Unresolved Scan Feedback", health["unresolved_scan_feedback"])
    with col4:
        st.metric("Total URL Rules", health["total_url_rules"])
        st.metric("Total App Feedback", health["total_app_feedback"])
else:
    st.warning("Could not fetch system health data.")
