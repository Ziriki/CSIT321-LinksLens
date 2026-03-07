import streamlit as st
from controllers import auth_controller

st.set_page_config(page_title="LinksLens Admin", layout="wide")

if st.session_state.get("access_token") is None:
    st.title("LinksLens Admin Portal")
    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log In"):
            auth_controller.handle_login(email, password)
else:
    user = auth_controller.get_current_user()
    if user:
        role_label = {1: "User", 2: "Moderator", 3: "Administrator"}.get(user["role_id"], "Unknown")
        st.sidebar.write(f"Logged in as **{role_label}**")
    st.sidebar.markdown("---")
    if st.sidebar.button("Log Out"):
        st.session_state["access_token"] = None
        st.rerun()

    st.title("LinksLens Admin Portal")
    st.success("You are logged in. Use the sidebar to navigate.")
