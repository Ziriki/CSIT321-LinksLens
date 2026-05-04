import streamlit as st
from controllers import auth_controller
from models import api_client
auth_controller.require_role(1)

st.title("System Dashboard")

health = api_client.fetch_system_health()
if not health:
    st.warning("Could not fetch system health data.")
    st.stop()

overall = health.get("overall_status", "unknown")
if overall == "operational":
    st.success("All Systems Operational")
elif overall == "degraded":
    st.warning("Degraded Performance")
else:
    st.error("Service Outage Detected")

st.markdown("---")
st.subheader("Component Status")

STATUS_ICON = {"operational": "🟢", "degraded": "🟡", "outage": "🔴"}

components = health.get("components", [])
cols = st.columns(len(components)) if components else []
for col, component in zip(cols, components):
    icon = STATUS_ICON.get(component["status"], "⚪")
    detail = component.get("detail", "")
    with col:
        st.metric(component["name"], f"{icon} {component['status'].capitalize()}")
        if detail:
            st.caption(detail)

st.markdown("---")
st.subheader("Pending Work")

pending = health.get("pending_work", {})
col1, col2 = st.columns(2)
with col1:
    st.metric("Scan Feedback Pending Review", pending.get("scan_feedback_pending_review", 0))
with col2:
    st.metric("App Feedback Unreviewed", pending.get("app_feedback_unreviewed", 0))

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Scans Today", health.get("activity", {}).get("scans_today", 0))
with col2:
    st.metric("Blacklisted Domains", health.get("url_rules", {}).get("blacklisted_domains", 0))
with col3:
    st.metric("Whitelisted Domains", health.get("url_rules", {}).get("whitelisted_domains", 0))
