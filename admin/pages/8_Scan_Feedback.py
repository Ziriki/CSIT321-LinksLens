import streamlit as st
import pandas as pd
from controllers import auth_controller
from models import api_client

st.set_page_config(page_title="Scan Feedback", layout="wide")
# Admin + Moderator (RoleID 1, 2)
current_user = auth_controller.require_role(1, 2)
auth_controller.render_sidebar()

st.title("Scan Feedback Review")
st.markdown("Verify scan results reported by users to ensure no false positives or false negatives.")

# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------
filter_option = st.radio("Filter", ["All", "Resolved", "Unresolved"], horizontal=True)
is_resolved = {"Unresolved": False, "Resolved": True, "All": None}[filter_option]

# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
search_query = st.text_input("Search", placeholder="Search by name, URL, status, comments...")

# ---------------------------------------------------------------------------
# Fetch enriched data
# ---------------------------------------------------------------------------
raw_data = api_client.fetch_scan_feedback_enriched(is_resolved)

if not raw_data:
    st.info("No scan feedback found.")
    st.stop()

df = pd.DataFrame(raw_data)

# Apply search filter
if search_query:
    display_cols_for_search = ["FeedbackID", "UserName", "UserEmail", "InitialURL",
                               "CurrentStatus", "SuggestedStatus", "Comments"]
    search_available = [c for c in display_cols_for_search if c in df.columns]
    mask = df[search_available].apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
    df = df[mask].reset_index(drop=True)
    raw_data = df.to_dict("records")

if df.empty:
    st.info("No scan feedback matching your search.")
    st.stop()

# Display columns (no IsResolved, no raw IDs that are uninformative)
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

# ---------------------------------------------------------------------------
# Detail panel — shown when a row is selected
# ---------------------------------------------------------------------------
selected_rows = event.selection.rows if event.selection else []

if selected_rows:
    row_idx = selected_rows[0]
    fb = raw_data[row_idx]

    st.markdown("---")
    st.subheader(f"Feedback #{fb['FeedbackID']} — Scan #{fb['ScanID']}")

    # Scan info
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Scanned URL:** {fb['InitialURL']}")
        st.markdown(f"**Redirect URL:** {fb.get('RedirectURL') or 'None'}")
        st.markdown(f"**Domain Age:** {fb.get('DomainAgeDays') or 'N/A'} days")
        st.markdown(f"**Server Location:** {fb.get('ServerLocation') or 'N/A'}")
    with col2:
        st.markdown(f"**Submitted by:** {fb['UserName']} ({fb['UserEmail']})")
        st.markdown(f"**Scanned at:** {fb.get('ScannedAt') or 'N/A'}")
        st.markdown(f"**Current Verdict:** `{fb['CurrentStatus']}`")
        st.markdown(f"**User suggests:** `{fb['SuggestedStatus']}`")

    if fb.get("Comments"):
        st.info(f"**User comment:** {fb['Comments']}")

    if fb.get("ScreenshotURL"):
        with st.expander("View Sandboxed Screenshot"):
            st.image(fb["ScreenshotURL"], caption="Sandboxed render of the website")

    # -----------------------------------------------------------------
    # Verdict dropdown + apply button
    # -----------------------------------------------------------------
    current = fb["CurrentStatus"]
    scan_id = fb["ScanID"]
    feedback_id = fb["FeedbackID"]

    all_statuses = ["SAFE", "SUSPICIOUS", "MALICIOUS"]
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
            api_client.resolve_scan_feedback(feedback_id)
            api_client.log_action(
                current_user["user_id"], "CONFIRMED_SCAN_VERDICT",
                f"Confirmed Scan #{scan_id} verdict as {current} (Feedback #{feedback_id}).",
            )
            st.success(f"Verdict kept as **{current}**. Feedback resolved.")
            st.rerun()
        else:
            new_status = verdict_choice.replace("Mark as ", "").upper()
            success = api_client.update_scan_status(scan_id, new_status)
            if success:
                api_client.resolve_scan_feedback(feedback_id)
                api_client.log_action(
                    current_user["user_id"], "UPDATED_SCAN_VERDICT",
                    f"Changed Scan #{scan_id} verdict from {current} to {new_status} (Feedback #{feedback_id}).",
                )
                st.success(f"Scan #{scan_id} updated to **{new_status}** and feedback resolved.")
                st.rerun()
            else:
                st.error("Failed to update scan status.")
