import streamlit as st
import pandas as pd
from controllers import auth_controller
from models import api_client

st.set_page_config(page_title="Scan History", layout="wide")
# Admin + Moderator (RoleID 1, 2)
auth_controller.require_role(1, 2)
auth_controller.render_sidebar()

st.title("Scan History")

PAGE_SIZE = 25

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
col_search, col_status, col_user = st.columns([3, 1, 1])
with col_search:
    search_url = st.text_input("Search by URL", placeholder="e.g. google.com")
with col_status:
    status_filter = st.selectbox("Status", ["All", "SAFE", "SUSPICIOUS", "MALICIOUS"])
with col_user:
    user_id_filter = st.number_input("User ID", min_value=0, step=1, value=0,
                                     help="0 = all users")

# ---------------------------------------------------------------------------
# Pagination state
# ---------------------------------------------------------------------------
if "scan_page" not in st.session_state:
    st.session_state["scan_page"] = 0

page = st.session_state["scan_page"]
skip = page * PAGE_SIZE

# ---------------------------------------------------------------------------
# Fetch data
# ---------------------------------------------------------------------------
records = api_client.fetch_scan_list(
    skip=skip,
    limit=PAGE_SIZE + 1,  # fetch one extra to know if there's a next page
    search_url=search_url if search_url else None,
    status_indicator=status_filter if status_filter != "All" else None,
    user_id=user_id_filter if user_id_filter > 0 else None,
)

has_next = len(records) > PAGE_SIZE
display_records = records[:PAGE_SIZE]

# ---------------------------------------------------------------------------
# Table with row selection
# ---------------------------------------------------------------------------
if not display_records:
    st.info("No scan records found.")
else:
    df = pd.DataFrame(display_records)
    columns = ["ScanID", "UserID", "InitialURL", "StatusIndicator",
                "DomainAgeDays", "ServerLocation", "ScannedAt"]
    available = [c for c in columns if c in df.columns]

    event = st.dataframe(
        df[available],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # Detail panel when a row is selected
    selected_rows = event.selection.rows if event.selection else []
    if selected_rows:
        row_idx = selected_rows[0]
        scan_id = int(df.iloc[row_idx]["ScanID"])
        data = api_client.fetch_scan_details(scan_id)

        if data:
            st.markdown("---")
            st.subheader(f"Scan #{data['ScanID']} Details")
            st.write(f"**Target URL:** {data['InitialURL']}")
            if data.get("RedirectURL"):
                st.write(f"**Redirect URL:** {data['RedirectURL']}")
            st.write(f"**Final Verdict:** `{data['StatusIndicator']}`")

            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Server Location:** {data.get('ServerLocation', 'N/A')}")
            with col2:
                st.warning(f"**Domain Age (Days):** {data.get('DomainAgeDays', 'N/A')}")

            if data.get("ScreenshotURL"):
                with st.expander("View Sandboxed Screenshot"):
                    st.image(data["ScreenshotURL"], caption="Sandboxed render of the website")

            if data.get("RawText"):
                with st.expander("View Extracted Raw Text"):
                    st.text(data["RawText"])

# ---------------------------------------------------------------------------
# Pagination controls
# ---------------------------------------------------------------------------
col_prev, col_info, col_next = st.columns([1, 4, 1])
with col_prev:
    if st.button("Previous", disabled=(page == 0)):
        st.session_state["scan_page"] = max(0, page - 1)
        st.rerun()
with col_info:
    start = skip + 1 if display_records else 0
    end = skip + len(display_records)
    st.markdown(f"Showing **{start}–{end}** (Page {page + 1})")
with col_next:
    if st.button("Next", disabled=(not has_next)):
        st.session_state["scan_page"] = page + 1
        st.rerun()
