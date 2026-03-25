import streamlit as st
from controllers import auth_controller, user_controller
from models import api_client
from config import LOGO_PATH, PAGE_LAYOUT
from utils import search_dataframe

st.set_page_config(page_title="User Management", page_icon=LOGO_PATH, layout=PAGE_LAYOUT)
# Admin only (RoleID 1)
current_user = auth_controller.require_role(1)
auth_controller.render_sidebar()

st.title("User Management")

ROLE_MAP = {1: "Administrator", 2: "Moderator", 3: "User"}
PAGE_SIZE = 20

# ---------------------------------------------------------------------------
# User table with pagination
# ---------------------------------------------------------------------------
all_df = user_controller.get_users_dataframe()
if all_df.empty:
    st.info("No users found.")
    st.stop()

# Map RoleID to label for display
all_df["Role"] = all_df["RoleID"].map(ROLE_MAP)

# Search
search_query = st.text_input("Search", placeholder="Search by name, email, role...")
all_df = search_dataframe(all_df, search_query, columns=["FullName", "EmailAddress", "Role"])

if "user_page" not in st.session_state:
    st.session_state["user_page"] = 0

total = len(all_df)
page = st.session_state["user_page"]
start = page * PAGE_SIZE
end = min(start + PAGE_SIZE, total)
page_df = all_df.iloc[start:end]

display_df = page_df[["UserID", "FullName", "EmailAddress", "Role"]]

event = st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

# Pagination controls
col_prev, col_info, col_next = st.columns([1, 4, 1])
with col_prev:
    if st.button("Previous", disabled=(page == 0), key="user_prev"):
        st.session_state["user_page"] = max(0, page - 1)
        st.rerun()
with col_info:
    st.markdown(f"Showing **{start + 1}–{end}** of {total} (Page {page + 1})")
with col_next:
    if st.button("Next", disabled=(end >= total), key="user_next"):
        st.session_state["user_page"] = page + 1
        st.rerun()

# ---------------------------------------------------------------------------
# Detect row selection
# ---------------------------------------------------------------------------
selected_rows = event.selection.rows if event.selection else []

if not selected_rows:
    st.stop()

row_idx = selected_rows[0]
uid = int(page_df.iloc[row_idx]["UserID"])
user_row = all_df[all_df["UserID"] == uid].iloc[0]

# Fetch extended details from /api/details/{uid}
details = api_client.fetch_user_detail(uid) or {}

st.markdown("---")
st.subheader(f"Editing User #{uid}")

col1, col2 = st.columns(2)
with col1:
    email = st.text_input("Email Address", value=user_row["EmailAddress"], key=f"edit_email_{uid}")
    role = st.selectbox(
        "Role",
        options=[1, 2, 3],
        index=[1, 2, 3].index(int(user_row["RoleID"])),
        format_func=lambda x: ROLE_MAP[x],
        key=f"edit_role_{uid}",
    )
    full_name = st.text_input("Full Name", value=details.get("FullName") or "", key=f"edit_name_{uid}")
    gender = st.selectbox(
        "Gender",
        options=["Male", "Female", "Other"],
        index=["Male", "Female", "Other"].index(details.get("Gender", "Other") or "Other"),
        key=f"edit_gender_{uid}",
    )
with col2:
    phone = st.text_input("Phone Number", value=details.get("PhoneNumber") or "", key=f"edit_phone_{uid}")
    address = st.text_input("Address", value=details.get("Address") or "", key=f"edit_address_{uid}")
    dob = st.text_input("Date of Birth (YYYY-MM-DD)", value=details.get("DateOfBirth") or "", key=f"edit_dob_{uid}")
    status_label = "Active" if user_row["IsActive"] else "Inactive"
    st.text_input("Status", value=status_label, disabled=True, key=f"edit_status_{uid}")

# Build change payload only from actual diffs
snapshot = {}
if email != user_row["EmailAddress"]:
    snapshot["EmailAddress"] = email
if role != int(user_row["RoleID"]):
    snapshot["RoleID"] = role
if full_name != (details.get("FullName") or ""):
    snapshot["FullName"] = full_name
if gender != (details.get("Gender") or "Other"):
    snapshot["Gender"] = gender
if phone != (details.get("PhoneNumber") or ""):
    snapshot["PhoneNumber"] = phone
if address != (details.get("Address") or ""):
    snapshot["Address"] = address
if dob != (details.get("DateOfBirth") or ""):
    snapshot["DateOfBirth"] = dob if dob else None

# Buttons
btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
with btn_col1:
    if st.button("Update", type="primary", key="btn_update"):
        if not snapshot:
            st.info("No changes to save.")
        else:
            account_payload = {}
            if "EmailAddress" in snapshot:
                account_payload["EmailAddress"] = snapshot["EmailAddress"]
            if "RoleID" in snapshot:
                account_payload["RoleID"] = snapshot["RoleID"]
            if account_payload:
                api_client.update_user_details(uid, account_payload)

            detail_payload = {k: v for k, v in snapshot.items() if k not in ("EmailAddress", "RoleID")}
            if detail_payload:
                api_client.update_user_profile(uid, detail_payload)

            changes = ", ".join(f"{k}={v}" for k, v in snapshot.items())
            api_client.log_action(
                current_user["user_id"], "UPDATED_USER",
                f"Updated User #{uid}: {changes}.",
            )
            st.session_state.pop("confirm_deactivate", None)
            st.cache_data.clear()
            st.rerun()

with btn_col2:
    if user_row["IsActive"]:
        if st.button("Deactivate", type="secondary", key="btn_deactivate"):
            st.session_state["confirm_deactivate"] = uid

# Deactivation confirmation dialog
if st.session_state.get("confirm_deactivate") == uid:
    st.warning(f"Are you sure you want to deactivate User #{uid}?")
    confirm_col1, confirm_col2 = st.columns(2)
    with confirm_col1:
        if st.button("Yes, deactivate", key="confirm_yes"):
            api_client.deactivate_user(uid)
            api_client.log_action(
                current_user["user_id"], "DEACTIVATED_USER",
                f"Deactivated User #{uid}.",
            )
            st.session_state.pop("confirm_deactivate", None)
            st.cache_data.clear()
            st.rerun()
    with confirm_col2:
        if st.button("Cancel", key="confirm_no"):
            st.session_state.pop("confirm_deactivate", None)
            st.rerun()
