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
# Fetch enriched data
# ---------------------------------------------------------------------------
raw_data = api_client.fetch_scan_feedback_enriched(is_resolved)

if not raw_data:
    st.info("No scan feedback found.")
    st.stop()

df = pd.DataFrame(raw_data)

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
    # Action buttons — change scan verdict or keep current
    # -----------------------------------------------------------------
    current = fb["CurrentStatus"]
    scan_id = fb["ScanID"]
    feedback_id = fb["FeedbackID"]

    # The other statuses the admin can change to (exclude current + PENDING)
    all_statuses = ["SAFE", "SUSPICIOUS", "MALICIOUS"]
    other_statuses = [s for s in all_statuses if s != current]

    st.markdown("### Verdict")
    cols = st.columns(len(other_statuses) + 1)

    # "Mark as X" buttons for each alternative status
    for i, new_status in enumerate(other_statuses):
        with cols[i]:
            if st.button(f"Mark as {new_status.title()}", key=f"mark_{new_status}"):
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

    # "Remain X" button to keep current status
    with cols[len(other_statuses)]:
        if st.button(f"Remain {current.title()}", key="remain"):
            api_client.resolve_scan_feedback(feedback_id)
            api_client.log_action(
                current_user["user_id"], "CONFIRMED_SCAN_VERDICT",
                f"Confirmed Scan #{scan_id} verdict as {current} (Feedback #{feedback_id}).",
            )
            st.success(f"Verdict kept as **{current}**. Feedback resolved.")
            st.rerun()
