import pandas as pd
import streamlit as st

from controllers import auth_controller
from models import api_client
from utils import (render_homograph_expander, render_redirect_chain_expander,
                   render_script_analysis_expander, render_ssl_expander,
                   scroll_to_bottom)

auth_controller.require_role(1, 2)

st.title("Scan History")

PAGE_SIZE = 10

st.session_state.setdefault("scanner_result_id", None)
st.session_state.setdefault("scanner_error", None)
st.session_state.setdefault("scan_page", 0)

# ── URL Scanner ──────────────────────────────────────────────────────────────

with st.expander("Scan a URL", expanded=False):
    if error_msg := st.session_state.get("scanner_error"):
        st.error(error_msg)
        st.session_state["scanner_error"] = None

    scan_input = st.text_input("URL to scan", placeholder="https://example.com", key="scanner_url_input")
    if st.button("Scan", key="scanner_submit") and scan_input.strip():
        url_to_scan = scan_input.strip()
        with st.spinner(f"Scanning `{url_to_scan}` — this may take up to 90 seconds…"):
            result = api_client.scan_url(url_to_scan)
        if result and result.get("scan_id"):
            st.session_state["scanner_result_id"] = result["scan_id"]
            st.session_state["scan_page"] = 0
            st.rerun()
        else:
            st.session_state["scanner_error"] = "Scan failed. Check the URL and try again."
            st.rerun()

# ── Filters ──────────────────────────────────────────────────────────────────

status_filter = st.radio("Status", ["All", "SAFE", "SUSPICIOUS", "MALICIOUS"], horizontal=True)

search = st.text_input("Search", placeholder="Search by URL or user name...")

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

scanner_id = st.session_state.get("scanner_result_id")
effective_scan_id = None

if not display_records:
    st.info("No scan records found.")
else:
    df = pd.DataFrame(display_records)
    df.rename(columns={"FullName": "User"}, inplace=True)
    if "DomainAgeDays" in df.columns:
        df["DomainAgeDays"] = df["DomainAgeDays"].astype("Int64")
    columns = ["ScanID", "User", "InitialURL", "StatusIndicator",
               "DomainAgeDays", "ServerLocation", "ScannedAt"]
    available = [c for c in columns if c in df.columns]

    def _highlight_new(row):
        if scanner_id and row["ScanID"] == scanner_id:
            return ["background-color: #d1fae5"] * len(row)
        return [""] * len(row)

    event = st.dataframe(
        df[available].style.apply(_highlight_new, axis=1),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = event.selection.rows if event.selection else []
    if selected_rows:
        effective_scan_id = int(df.iloc[selected_rows[0]]["ScanID"])
    elif scanner_id and any(r["ScanID"] == scanner_id for r in display_records):
        effective_scan_id = scanner_id

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

if effective_scan_id:
    scroll_to_bottom(f"scan_{effective_scan_id}")
    data = api_client.fetch_scan_details(effective_scan_id)
    if data:
        if scanner_id == effective_scan_id:
            st.success(f"Scan complete — result for `{data['InitialURL']}` is **{data['StatusIndicator']}**")

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
            _verdict_color = {
                "MALICIOUS": "#dc2626",
                "SUSPICIOUS": "#d97706",
                "SAFE": "#16a34a",
                "UNAVAILABLE": "#6b7280",
            }.get(data["StatusIndicator"], "#6b7280")
            st.markdown(
                f"**Final Verdict:** <span style='color:{_verdict_color};font-weight:600'>{data['StatusIndicator']}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Scanned At:** {data.get('ScannedAt', 'N/A')}")
        with col2:
            st.markdown(f"**IP Address:** {data.get('IpAddress') or 'N/A'}")
            st.markdown(f"**Country:** {data.get('ServerLocation') or 'N/A'}")
            st.markdown(f"**Hosting Provider:** {data.get('AsnName') or 'N/A'}")
            st.markdown(f"**Domain Age:** {data.get('DomainAgeDays') or 'N/A'} days")
            user_name = next(
                (r.get("FullName") for r in display_records if r["ScanID"] == effective_scan_id),
                None,
            )
            st.markdown(f"**User:** {user_name or data.get('UserID', 'N/A')}")

        render_ssl_expander(data.get("SslInfo") or {})

        if data.get("ScreenshotURL"):
            with st.expander("Website Screenshot"):
                st.image(data["ScreenshotURL"], caption="Sandboxed render of the website")

        render_redirect_chain_expander(data.get("RedirectChain") or [])
        render_script_analysis_expander(data.get("ScriptAnalysis") or {})
        render_homograph_expander(data.get("HomographAnalysis") or {})
