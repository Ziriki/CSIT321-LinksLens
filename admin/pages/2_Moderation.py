import streamlit as st
from controllers import auth_controller, moderation_controller
from config import LOGO_PATH, PAGE_LAYOUT

st.set_page_config(page_title="Moderation Queue", page_icon=LOGO_PATH, layout=PAGE_LAYOUT)
# Admin + Moderator (RoleID 1, 2)
user = auth_controller.require_role(1, 2)
auth_controller.render_sidebar()

st.title("Moderation Queue")
df = moderation_controller.get_pending_requests_dataframe()

if df.empty:
    st.info("No pending blacklist requests.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("### Review a Request")
    target_id = st.number_input("Request ID", min_value=1, step=1)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Approve"):
            moderation_controller.handle_review_action(target_id, "APPROVED", user["user_id"])
    with col2:
        if st.button("Reject"):
            moderation_controller.handle_review_action(target_id, "REJECTED", user["user_id"])
