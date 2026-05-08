import threading
import time
import uuid

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

# Module-level dict for thread → main-thread communication.
# st.session_state is not safely writable from background threads;
# this dict is shared memory accessible from any thread.
# Key: scan_uuid  Value: result dict (success) | False (failure)
# Absent key means scan is still in progress.
_SCAN_RESULTS: dict[str, dict | bool] = {}

st.session_state.setdefault("scanner_result_id", None)
st.session_state.setdefault("scan_running", False)
st.session_state.setdefault("scan_start_time", None)
st.session_state.setdefault("scan_url_in_progress", "")
st.session_state.setdefault("scanner_error", None)
st.session_state.setdefault("scan_page", 0)
st.session_state.setdefault("scan_key", None)

_SCAN_STEPS = [
    (0,  "Checking Google Safe Browsing database…",  10),
    (2,  "Submitting URL to security scanner…",       22),
    (4,  "Waiting for scan analysis to complete…",    35),
    (14, "Retrieving server location…",               50),
    (17, "Checking domain registration age…",         60),
    (19, "Analysing redirect chain…",                 68),
    (21, "Analysing page scripts…",                   75),
    (35, "Finalising verdict…",                       83),
    (55, "Still analysing, almost there…",            90),
    (75, "Completing script analysis…",               95),
    (85, "Wrapping up…",                              97),
]


def _do_scan(scan_key: str, url: str) -> None:
    try:
        result = api_client.scan_url(url)
        _SCAN_RESULTS[scan_key] = result if (result and result.get("scan_id")) else False
    except Exception:
        _SCAN_RESULTS[scan_key] = False


# ── Scan state machine ───────────────────────────────────────────────────────

if st.session_state["scan_running"]:
    scan_key = st.session_state["scan_key"]

    if scan_key in _SCAN_RESULTS:
        # Scan completed — move result into session state and clear
        outcome = _SCAN_RESULTS.pop(scan_key)
        st.session_state["scan_running"] = False
        st.session_state["scan_key"] = None
        if outcome:
            st.session_state["scanner_result_id"] = outcome["scan_id"]
            st.session_state["scan_page"] = 0
        else:
            st.session_state["scanner_error"] = "Scan failed. Check the URL and try again."
        st.rerun()
    else:
        elapsed = time.time() - st.session_state["scan_start_time"]

        current_msg, current_progress = _SCAN_STEPS[0][1], _SCAN_STEPS[0][2]
        for at, msg, prog in _SCAN_STEPS:
            if elapsed >= at:
                current_msg, current_progress = msg, prog
            else:
                break

        st.markdown(f"**Scanning:** `{st.session_state['scan_url_in_progress']}`")
        st.progress(current_progress / 100, text=current_msg)
        time.sleep(2)
        st.rerun()

# ── URL Scanner ──────────────────────────────────────────────────────────────

with st.expander("Scan a URL", expanded=False):
    if error_msg := st.session_state.get("scanner_error"):
        st.error(error_msg)
        st.session_state["scanner_error"] = None

    scan_input = st.text_input("URL to scan", placeholder="https://example.com", key="scanner_url_input")
    if st.button("Scan", key="scanner_submit") and scan_input.strip():
        scan_key = str(uuid.uuid4())
        url_to_scan = scan_input.strip()
        st.session_state["scan_running"] = True
        st.session_state["scan_start_time"] = time.time()
        st.session_state["scan_url_in_progress"] = url_to_scan
        st.session_state["scan_key"] = scan_key
        st.session_state["scanner_error"] = None
        threading.Thread(target=_do_scan, args=(scan_key, url_to_scan), daemon=True).start()
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
