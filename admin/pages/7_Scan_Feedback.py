import streamlit as st
import pandas as pd
from controllers import auth_controller, scan_feedback_controller
from utils import search_dataframe, render_ssl_expander, render_redirect_chain_expander, render_script_analysis_expander, render_homograph_expander, scroll_to_bottom

current_user = auth_controller.require_role(1, 2)

st.title("Scan Feedback Review")
st.markdown("Verify scan results reported by users to ensure no false positives or false negatives.")

filter_option = st.radio("Filter", ["All", "Resolved", "Unresolved"], horizontal=True)
is_resolved = {"Unresolved": False, "Resolved": True, "All": None}[filter_option]

search_query = st.text_input("Search", placeholder="Search by name, URL, status, comments...")

raw_data = scan_feedback_controller.get_enriched_feedback(is_resolved)

if not raw_data:
    st.info("No scan feedback found.")
    st.stop()

df = pd.DataFrame(raw_data)

if search_query:
    search_cols = ["FeedbackID", "UserName", "UserEmail", "InitialURL",
                   "CurrentStatus", "SuggestedStatus", "Comments"]
    available = [c for c in search_cols if c in df.columns]
    df = search_dataframe(df, search_query, columns=available)
    raw_data = df.to_dict("records")

if df.empty:
    st.info("No scan feedback matching your search.")
    st.stop()

display_cols = ["FeedbackID", "UserName", "UserEmail", "InitialURL",
                "CurrentStatus", "SuggestedStatus", "Comments"]
available = [c for c in display_cols if c in df.columns]
display_df = df[available]

event = st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

selected_rows = event.selection.rows if event.selection else []

if selected_rows:
    row_idx = selected_rows[0]
    fb = raw_data[row_idx]
    scroll_to_bottom(f"feedback_{fb['FeedbackID']}")

    st.markdown("---")
    st.subheader(f"Feedback #{fb['FeedbackID']} — Scan #{fb['ScanID']}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Scanned URL:** {fb['InitialURL']}")
        if fb.get("RedirectURL"):
            st.markdown(f"**Redirect URL:** {fb['RedirectURL']}")
        if fb.get("PageTitle"):
            st.markdown(f"**Page Title:** {fb['PageTitle']}")
        if fb.get("ApexDomain"):
            st.markdown(f"**Registered Domain:** `{fb['ApexDomain']}`")
        st.markdown(f"**Domain Age:** {fb.get('DomainAgeDays') or 'N/A'} days")
    with col2:
        st.markdown(f"**Submitted by:** {fb['UserName']} ({fb['UserEmail']})")
        st.markdown(f"**Feedback submitted:** {fb.get('CreatedAt') or 'N/A'}")
        st.markdown(f"**Scanned at:** {fb.get('ScannedAt') or 'N/A'}")
        st.markdown(f"**IP Address:** {fb.get('IpAddress') or 'N/A'}")
        st.markdown(f"**Country:** {fb.get('ServerLocation') or 'N/A'}")
        st.markdown(f"**Hosting Provider:** {fb.get('AsnName') or 'N/A'}")
        st.markdown(f"**Current Verdict:** `{fb['CurrentStatus']}`")
        st.markdown(f"**User suggests:** `{fb['SuggestedStatus']}`")

    render_ssl_expander(fb.get("SslInfo") or {})

    if fb.get("Comments"):
        st.info(f"**User comment:** {fb['Comments']}")

    if fb.get("ScreenshotURL"):
        with st.expander("Website Screenshot"):
            st.image(fb["ScreenshotURL"], caption="Sandboxed render of the website")

    render_redirect_chain_expander(fb.get("RedirectChain") or [])
    render_script_analysis_expander(fb.get("ScriptAnalysis") or {})
    render_homograph_expander(fb.get("HomographAnalysis") or {})

    current = fb["CurrentStatus"]
    scan_id = fb["ScanID"]
    feedback_id = fb["FeedbackID"]

    all_statuses = ["SAFE", "MALICIOUS"]
    options = [f"Remain {current.title()}"] + [f"Mark as {s.title()}" for s in all_statuses if s != current]

    st.markdown("### Verdict")
    col_dd, col_btn = st.columns([3, 1])
    with col_dd:
        verdict_choice = st.selectbox("Select verdict", options, key=f"verdict_{feedback_id}")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        apply = st.button("Apply", key=f"apply_{feedback_id}")

    if apply:
        if verdict_choice.startswith("Remain"):
            scan_feedback_controller.handle_confirm_verdict(feedback_id, scan_id, current, current_user["user_id"])
        else:
            new_status = verdict_choice.replace("Mark as ", "").upper()
            if not scan_feedback_controller.handle_update_verdict(feedback_id, scan_id, current, new_status, current_user["user_id"]):
                st.error("Failed to update scan status.")
