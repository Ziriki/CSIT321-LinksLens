import streamlit as st
from controllers import auth_controller
from config import LOGO_PATH, PAGE_LAYOUT

st.set_page_config(page_title="LinksLens Admin", page_icon=LOGO_PATH, layout=PAGE_LAYOUT)

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
    st.image(LOGO_PATH, width=180)
    st.title("LinksLens Admin Portal")

    if st.session_state.pop("session_expired", False):
        st.warning("Your session has expired. Please log in again.")

    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log In"):
            auth_controller.handle_login(email, password)
else:
    user = auth_controller.get_current_user()
    role_id = user["role_id"] if user else None

    _ADMIN_PAGES = [
        st.Page("pages/1_Dashboard.py", title="Dashboard"),
        st.Page("pages/3_User_Management.py", title="User Management"),
        st.Page("pages/4_App_Feedback.py", title="App Feedback"),
        st.Page("pages/5_Action_History_Log.py", title="Action History Log"),
    ]
    _SHARED_PAGES = [
        st.Page("pages/6_URL_Registry.py", title="URL Registry"),
        st.Page("pages/7_Scan_History.py", title="Scan History"),
        st.Page("pages/8_Scan_Feedback.py", title="Scan Feedback"),
        st.Page("pages/9_Threat_Intelligence.py", title="Threat Intelligence"),
    ]

    pages = (_ADMIN_PAGES + _SHARED_PAGES) if role_id == 1 else _SHARED_PAGES

    pg = st.navigation(pages)
    auth_controller.render_sidebar()
    pg.run()
