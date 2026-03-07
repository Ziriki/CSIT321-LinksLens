# pages/3_User_Management.py
import streamlit as st
from controllers import auth_controller, user_controller

st.set_page_config(page_title="User Management", layout="wide")
auth_controller.require_auth()

st.title("User Management")
df = user_controller.get_users_dataframe()
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("### Update User Role")
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    target_user = st.number_input("Target User ID", min_value=1, step=1)
with col2:
    # Assuming RoleID 1=Admin, 2=Moderator, 3=User based on your earlier schema
    new_role = st.selectbox("Assign New Role", options=[1, 2, 3], format_func=lambda x: {1: "Admin", 2: "Moderator", 3: "User"}[x])
with col3:
    st.write("")
    st.write("")
    if st.button("Update Role"):
        user_controller.handle_role_update(target_user, new_role)