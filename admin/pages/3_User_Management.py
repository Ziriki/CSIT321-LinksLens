import streamlit as st
from controllers import user_controller

st.title("User Management")
df = user_controller.get_users_dataframe()
st.dataframe(df)

target_user = st.number_input("Enter User ID to Deactivate", min_value=1)
if st.button("Deactivate User"):
    user_controller.handle_deactivation(target_user)