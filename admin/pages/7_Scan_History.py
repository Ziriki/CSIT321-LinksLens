import streamlit as st
import pandas as pd
from utils import render_ssl_expander, render_redirect_chain_expander, render_script_analysis_expander, render_homograph_expander, scroll_to_bottom
from controllers import auth_controller
from models import api_client
auth_controller.require_role(1, 2)

st.title("Scan History")

PAGE_SIZE = 10

status_filter = st.radio("Status", ["All", "SAFE", "SUSPICIOUS", "MALICIOUS"], horizontal=True)

search = st.text_input("Search", placeholder="Search by URL or user name...")

if "scan_page" not in st.session_state:
    st.session_state["scan_page"] = 0

page = st.session_state["scan_page"]
skip = page * PAGE_SIZE

records = api_client.fetch_scan_list(
    skip=skip,
    limit=PAGE_SIZE + 1,
    search=search if search else None,
    status_indicator=status_filter if status_filter != "All" else None,
)

has_next = len(records) > PAGE_SIZE
display_records = records[:PAGE_SIZE]

selected_scan_id = None

if not display_records:
    st.info("No scan records found.")
else:
    df = pd.DataFrame(display_records)
    df.rename(columns={"FullName": "User"}, inplace=True)
    columns = ["ScanID", "User", "InitialURL", "StatusIndicator",
                "DomainAgeDays", "ServerLocation", "ScannedAt"]
    available = [c for c in columns if c in df.columns]

    event = st.dataframe(
        df[available],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = event.selection.rows if event.selection else []
    if selected_rows:
        selected_scan_id = int(df.iloc[selected_rows[0]]["ScanID"])

col_prev, col_info, col_next = st.columns([1, 4, 1])
with col_prev:
    if st.button("Previous", disabled=(page == 0)):
        st.session_state["scan_page"] = max(0, page - 1)
        st.rerun()
with col_info:
    start_label = skip + 1 if display_records else 0
    end_label = skip + len(display_records)
    st.markdown(f"Showing **{start_label}–{end_label}** (Page {page + 1})")
with col_next:
    if st.button("Next", disabled=(not has_next)):
        st.session_state["scan_page"] = page + 1
        st.rerun()

if selected_scan_id:
    scroll_to_bottom(f"scan_{selected_scan_id}")
    data = api_client.fetch_scan_details(selected_scan_id)
    if data:
        st.markdown("---")
        st.subheader(f"Scan #{data['ScanID']} Details")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Target URL:** {data['InitialURL']}")
            if data.get("RedirectURL"):
                st.markdown(f"**Redirect URL:** {data['RedirectURL']}")
            if data.get("PageTitle"):
                st.markdown(f"**Page Title:** {data['PageTitle']}")
            if data.get("ApexDomain"):
                st.markdown(f"**Registered Domain:** `{data['ApexDomain']}`")
            st.markdown(f"**Final Verdict:** `{data['StatusIndicator']}`")
            st.markdown(f"**Scanned At:** {data.get('ScannedAt', 'N/A')}")
        with col2:
            st.markdown(f"**IP Address:** {data.get('IpAddress') or 'N/A'}")
            st.markdown(f"**Country:** {data.get('ServerLocation') or 'N/A'}")
            st.markdown(f"**Hosting Provider:** {data.get('AsnName') or 'N/A'}")
            st.markdown(f"**Domain Age:** {data.get('DomainAgeDays') or 'N/A'} days")
            st.markdown(f"**User ID:** {data.get('UserID', 'N/A')}")

        render_ssl_expander(data.get("SslInfo") or {})

        if data.get("ScreenshotURL"):
            with st.expander("Website Screenshot"):
                st.image(data["ScreenshotURL"], caption="Sandboxed render of the website")

        render_redirect_chain_expander(data.get("RedirectChain") or [])
        render_script_analysis_expander(data.get("ScriptAnalysis") or {})
        render_homograph_expander(data.get("HomographAnalysis") or {})
