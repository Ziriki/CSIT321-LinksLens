def handle_login(email, password):
    if not email or not password:
        st.error("Please fill in both fields.")
        return False
    with st.spinner("Authenticating..."):
        response = api_client.authenticate_user(email, password)
        if response.status_code == 200:
            st.session_state["access_token"] = response.json()["access_token"]
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Login failed. Check credentials.")