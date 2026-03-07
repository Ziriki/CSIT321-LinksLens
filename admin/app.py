import streamlit as st
from controllers import auth_controller

if st.session_state.get("access_token") is None:
    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log In"):
            auth_controller.handle_login(email, password)
else:
    st.success("You are logged in.")
    if st.sidebar.button("Log Out"):
        st.session_state["access_token"] = None
        st.rerun()