import streamlit as st
from controllers import auth_controller, rules_controller
from config import LOGO_PATH, PAGE_LAYOUT
from utils import search_dataframe

st.set_page_config(page_title="URL Registry", page_icon=LOGO_PATH, layout=PAGE_LAYOUT)
# Admin + Moderator (RoleID 1, 2)
auth_controller.require_role(1, 2)
auth_controller.render_sidebar()

st.title("URL Registry")
st.markdown("View the global Blacklist and Whitelist active in the system.")

PAGE_SIZE = 20

df = rules_controller.get_rules_dataframe()
if df.empty:
    st.info("The master list is currently empty.")
    st.stop()

list_type = st.radio("Filter List Type", ["All", "Blacklist", "Whitelist"], horizontal=True)
filter_map = {"Blacklist": "BLACKLIST", "Whitelist": "WHITELIST"}
if list_type != "All":
    df = df[df["ListType"] == filter_map[list_type]].reset_index(drop=True)

# Search
search_query = st.text_input("Search", placeholder="Search by URL domain, added by name...")
df = search_dataframe(df, search_query)

if "rules_page" not in st.session_state:
    st.session_state["rules_page"] = 0

total = len(df)
page = st.session_state["rules_page"]
start = page * PAGE_SIZE
end = min(start + PAGE_SIZE, total)

if total == 0:
    st.info("No rules found for this filter.")
else:
    st.dataframe(df.iloc[start:end], use_container_width=True, hide_index=True)

    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("Previous", disabled=(page == 0)):
            st.session_state["rules_page"] = max(0, page - 1)
            st.rerun()
    with col_info:
        st.markdown(f"Showing **{start + 1}–{end}** of {total} (Page {page + 1})")
    with col_next:
        if st.button("Next", disabled=(end >= total)):
            st.session_state["rules_page"] = page + 1
            st.rerun()
