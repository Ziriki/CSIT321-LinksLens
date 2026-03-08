import streamlit as st
from controllers import auth_controller, user_controller

st.set_page_config(page_title="User Management", layout="wide")
# Admin only (RoleID 1)
auth_controller.require_role(1)

st.title("User Management")
df = user_controller.get_users_dataframe()
if df.empty:
    st.info("No users found.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

st.markdown("### Update User Role")
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    target_user = st.number_input("Target User ID", min_value=1, step=1)
with col2:
    new_role = st.selectbox(
        "Assign New Role",
        options=[1, 2, 3],
        format_func=lambda x: {1: "Administrator", 2: "Moderator", 3: "User"}[x],
    )
with col3:
    st.write("")
    st.write("")
    if st.button("Update Role"):
        user_controller.handle_role_update(target_user, new_role)

st.markdown("### Deactivate User")
col1, col2 = st.columns([1, 3])
with col1:
    deactivate_id = st.number_input("User ID to Deactivate", min_value=1, step=1)
with col2:
    st.write("")
    st.write("")
    if st.button("Deactivate"):
        user_controller.handle_deactivation(deactivate_id)
