import streamlit as st
from controllers import auth_controller, user_controller
from controllers.auth_controller import ROLE_LABELS
from models import api_client
from config import LOGO_PATH, PAGE_LAYOUT
from utils import search_dataframe, render_pagination, scroll_to_bottom

st.set_page_config(page_title="User Management", page_icon=LOGO_PATH, layout=PAGE_LAYOUT)
current_user = auth_controller.require_role(1)
auth_controller.render_sidebar()

st.title("User Management")

PAGE_SIZE = 20

all_df = user_controller.get_users_dataframe()
if all_df.empty:
    st.info("No users found.")
    st.stop()

all_df["Role"] = all_df["RoleID"].map(ROLE_LABELS)
all_df["Status"] = all_df["IsActive"].map({True: "Active", False: "Inactive"})

search_query = st.text_input("Search", placeholder="Search by name, email, role...")
all_df = search_dataframe(all_df, search_query, columns=["FullName", "EmailAddress", "Role", "Status"])

total = len(all_df)
start, end = render_pagination("user_page", total, PAGE_SIZE)
page_df = all_df.iloc[start:end]

event = st.dataframe(
    page_df[["UserID", "FullName", "EmailAddress", "Role", "Status"]],
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

selected_rows = event.selection.rows if event.selection else []

if not selected_rows:
    st.stop()

row_idx = selected_rows[0]
uid = int(page_df.iloc[row_idx]["UserID"])
scroll_to_bottom(f"user_{uid}")
user_row = all_df[all_df["UserID"] == uid].iloc[0]

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
        format_func=lambda x: ROLE_LABELS[x],
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
            st.session_state["confirm_status_change"] = (uid, "deactivate")
    else:
        if st.button("Activate", type="secondary", key="btn_activate"):
            st.session_state["confirm_status_change"] = (uid, "activate")

pending = st.session_state.get("confirm_status_change")
if pending and pending[0] == uid:
    action = pending[1]
    st.warning(f"Are you sure you want to {action} User #{uid}?")
    confirm_col1, confirm_col2 = st.columns(2)
    with confirm_col1:
        if st.button(f"Yes, {action}", key="confirm_yes"):
            if action == "deactivate":
                api_client.deactivate_user(uid)
                api_client.log_action(current_user["user_id"], "DEACTIVATED_USER", f"Deactivated User #{uid}.")
            else:
                api_client.activate_user(uid)
                api_client.log_action(current_user["user_id"], "ACTIVATED_USER", f"Activated User #{uid}.")
            st.session_state.pop("confirm_status_change", None)
            st.cache_data.clear()
            st.rerun()
    with confirm_col2:
        if st.button("Cancel", key="confirm_no"):
            st.session_state.pop("confirm_status_change", None)
            st.rerun()
