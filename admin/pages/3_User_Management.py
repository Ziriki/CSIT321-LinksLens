import streamlit as st
from controllers import auth_controller, user_controller
from models import api_client

st.set_page_config(page_title="User Management", layout="wide")
# Admin only (RoleID 1)
auth_controller.require_role(1)
auth_controller.render_sidebar()

st.title("User Management")

ROLE_MAP = {1: "Administrator", 2: "Moderator", 3: "User"}

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "selected_user_id" not in st.session_state:
    st.session_state["selected_user_id"] = None
if "edit_snapshot" not in st.session_state:
    st.session_state["edit_snapshot"] = {}

# ---------------------------------------------------------------------------
# User table
# ---------------------------------------------------------------------------
df = user_controller.get_users_dataframe()
if df.empty:
    st.info("No users found.")
    st.stop()

# Map RoleID to label for display
display_df = df.copy()
display_df["Role"] = display_df["RoleID"].map(ROLE_MAP)
display_df = display_df[["UserID", "EmailAddress", "Role", "IsActive"]]

event = st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

# ---------------------------------------------------------------------------
# Detect row selection
# ---------------------------------------------------------------------------
selected_rows = event.selection.rows if event.selection else []

if selected_rows:
    row_idx = selected_rows[0]
    clicked_user_id = int(df.iloc[row_idx]["UserID"])

    # If the admin switched to a different user while having unsaved edits
    prev_id = st.session_state.get("selected_user_id")
    if prev_id is not None and prev_id != clicked_user_id and st.session_state.get("edit_snapshot"):
        st.warning(
            f"You have unsaved changes for User {prev_id}. "
            "Switch anyway? Click **Discard** to continue or **Save** to save first."
        )
        col_save, col_discard = st.columns(2)
        with col_save:
            if st.button("Save changes", key="save_before_switch"):
                _snap = st.session_state["edit_snapshot"]
                # Save account-level fields
                account_payload = {}
                if "EmailAddress" in _snap:
                    account_payload["EmailAddress"] = _snap["EmailAddress"]
                if "RoleID" in _snap:
                    account_payload["RoleID"] = _snap["RoleID"]
                if account_payload:
                    api_client.update_user_details(prev_id, account_payload)
                # Save detail-level fields
                detail_payload = {k: v for k, v in _snap.items() if k not in ("EmailAddress", "RoleID")}
                if detail_payload:
                    api_client.update_user_profile(prev_id, detail_payload)
                st.session_state["edit_snapshot"] = {}
                st.session_state["selected_user_id"] = clicked_user_id
                st.success(f"Changes saved for User {prev_id}.")
                st.rerun()
        with col_discard:
            if st.button("Discard", key="discard_switch"):
                st.session_state["edit_snapshot"] = {}
                st.session_state["selected_user_id"] = clicked_user_id
                st.rerun()
        st.stop()

    st.session_state["selected_user_id"] = clicked_user_id

# ---------------------------------------------------------------------------
# Edit panel — only shown when a user is selected
# ---------------------------------------------------------------------------
if st.session_state["selected_user_id"] is not None:
    uid = st.session_state["selected_user_id"]
    user_row = df[df["UserID"] == uid].iloc[0]

    # Fetch extended details from /api/details/{uid}
    details = api_client.fetch_user_detail(uid) or {}

    st.markdown("---")
    st.subheader(f"Editing User #{uid}")

    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input("Email Address", value=user_row["EmailAddress"], key="edit_email")
        role = st.selectbox(
            "Role",
            options=[1, 2, 3],
            index=[1, 2, 3].index(int(user_row["RoleID"])),
            format_func=lambda x: ROLE_MAP[x],
            key="edit_role",
        )
        full_name = st.text_input("Full Name", value=details.get("FullName") or "", key="edit_name")
        gender = st.selectbox(
            "Gender",
            options=["Male", "Female", "Other"],
            index=["Male", "Female", "Other"].index(details.get("Gender", "Other") or "Other"),
            key="edit_gender",
        )
    with col2:
        phone = st.text_input("Phone Number", value=details.get("PhoneNumber") or "", key="edit_phone")
        address = st.text_input("Address", value=details.get("Address") or "", key="edit_address")
        dob = st.text_input("Date of Birth (YYYY-MM-DD)", value=details.get("DateOfBirth") or "", key="edit_dob")
        status_label = "Active" if user_row["IsActive"] else "Inactive"
        st.text_input("Status", value=status_label, disabled=True)

    # Track what changed
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
    st.session_state["edit_snapshot"] = snapshot

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

                st.session_state["edit_snapshot"] = {}
                st.success(f"User {uid} updated successfully!")
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
                st.session_state.pop("confirm_deactivate", None)
                st.session_state["edit_snapshot"] = {}
                st.success(f"User {uid} deactivated.")
                st.rerun()
        with confirm_col2:
            if st.button("Cancel", key="confirm_no"):
                st.session_state.pop("confirm_deactivate", None)
                st.rerun()
