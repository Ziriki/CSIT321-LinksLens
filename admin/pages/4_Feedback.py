import streamlit as st
from controllers import auth_controller, feedback_controller

st.set_page_config(page_title="App Feedback", layout="wide")
# Admin only (RoleID 1)
auth_controller.require_role(1)
auth_controller.render_sidebar()

st.title("App Feedback")

PAGE_SIZE = 20

df = feedback_controller.get_feedback_dataframe()
if df.empty:
    st.info("No feedback submitted yet.")
    st.stop()

# Sort descending by CreatedAt
df = df.sort_values(by="CreatedAt", ascending=False).reset_index(drop=True)

if "feedback_page" not in st.session_state:
    st.session_state["feedback_page"] = 0

total = len(df)
page = st.session_state["feedback_page"]
start = page * PAGE_SIZE
end = min(start + PAGE_SIZE, total)

st.dataframe(df.iloc[start:end], use_container_width=True, hide_index=True)

col_prev, col_info, col_next = st.columns([1, 4, 1])
with col_prev:
    if st.button("Previous", disabled=(page == 0)):
        st.session_state["feedback_page"] = max(0, page - 1)
        st.rerun()
with col_info:
    st.markdown(f"Showing **{start + 1}–{end}** of {total} (Page {page + 1})")
with col_next:
    if st.button("Next", disabled=(end >= total)):
        st.session_state["feedback_page"] = page + 1
        st.rerun()
