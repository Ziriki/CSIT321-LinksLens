import streamlit as st
from controllers import auth_controller

st.set_page_config(page_title="LinksLens Admin", layout="wide")

if st.session_state.get("access_token") is None:
    # Hide sidebar page navigation before login
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"] { display: none; }
            section[data-testid="stSidebar"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("LinksLens Admin Portal")
    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log In"):
            auth_controller.handle_login(email, password)
else:
    auth_controller.render_sidebar()

    st.title("LinksLens Admin Portal")
    st.success("You are logged in. Use the sidebar to navigate.")
