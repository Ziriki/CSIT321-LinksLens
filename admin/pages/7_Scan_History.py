import streamlit as st
from controllers import auth_controller, scan_history_controller

st.set_page_config(page_title="Scan Forensics", layout="wide")
# Moderator + Admin (RoleID 2, 3)
auth_controller.require_role(2, 3)

st.title("Scan Forensics Viewer")
st.markdown("Perform a deep-dive analysis on a specific scan record.")

scan_id = st.number_input("Enter Scan ID to investigate:", min_value=1, step=1)

if st.button("Fetch Forensic Data"):
    data = scan_history_controller.get_forensic_data(scan_id)
    if data:
        st.subheader(f"Results for Scan #{data['ScanID']}")
        st.write(f"**Target URL:** {data['InitialURL']}")
        st.write(f"**Final Verdict:** {data['StatusIndicator']}")

        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Server Location:** {data.get('ServerLocation', 'N/A')}")
        with col2:
            st.warning(f"**Domain Age (Days):** {data.get('DomainAgeDays', 'N/A')}")

        st.markdown("### Safe Static Screenshot")
        if data.get("ScreenshotURL"):
            st.image(data["ScreenshotURL"], caption="Sandboxed render of the website")
        else:
            st.info("No screenshot captured for this scan.")

        with st.expander("View Extracted Raw Text"):
            st.text(data.get("RawText", "No text extracted."))
