import streamlit as st
from controllers import auth_controller, action_history_controller

st.set_page_config(page_title="Action History Log", layout="wide")
# Admin only (RoleID 1)
auth_controller.require_role(1)
auth_controller.render_sidebar()

st.title("Action History Log")
st.markdown("Immutable record of all moderator and admin actions.")

PAGE_SIZE = 20

df = action_history_controller.get_audit_dataframe()
if df.empty:
    st.info("No action history logs found.")
    st.stop()

# Already sorted descending by LogID in controller, reset index
df = df.reset_index(drop=True)

# Search
search_query = st.text_input("Search", placeholder="Search by name, action type, action...")
if search_query:
    mask = df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
    df = df[mask].reset_index(drop=True)

if "history_page" not in st.session_state:
    st.session_state["history_page"] = 0

total = len(df)
page = st.session_state["history_page"]
start = page * PAGE_SIZE
end = min(start + PAGE_SIZE, total)

st.dataframe(df.iloc[start:end], use_container_width=True, hide_index=True)

col_prev, col_info, col_next = st.columns([1, 4, 1])
with col_prev:
    if st.button("Previous", disabled=(page == 0)):
        st.session_state["history_page"] = max(0, page - 1)
        st.rerun()
with col_info:
    st.markdown(f"Showing **{start + 1}–{end}** of {total} (Page {page + 1})")
with col_next:
    if st.button("Next", disabled=(end >= total)):
        st.session_state["history_page"] = page + 1
        st.rerun()
