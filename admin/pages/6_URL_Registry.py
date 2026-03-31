import streamlit as st
from controllers import auth_controller, rules_controller
from models import api_client
from config import LOGO_PATH, PAGE_LAYOUT
from utils import search_dataframe

st.set_page_config(page_title="URL Registry", page_icon=LOGO_PATH, layout=PAGE_LAYOUT)
# Admin + Moderator (RoleID 1, 2)
current_user = auth_controller.require_role(1, 2)
auth_controller.render_sidebar()

st.title("URL Registry")

# --- Add new rule ---
with st.expander("Submit a Domain to Blacklist / Whitelist", expanded=False):
    with st.form("add_rule_form", clear_on_submit=True):
        domain = st.text_input("Domain", placeholder="e.g. example.com")
        list_type = st.selectbox("List Type", ["BLACKLIST", "WHITELIST"])
        submitted = st.form_submit_button("Submit")

    if submitted:
        domain = domain.strip().lower()
        if not domain:
            st.warning("Please enter a domain.")
        else:
            if api_client.create_url_rule(domain, list_type, current_user["user_id"]):
                api_client.log_action(current_user["user_id"], "URL Rule", f"Added {domain} to {list_type}")
                st.success(f"{domain} added to {list_type} successfully.")
                st.rerun()
            else:
                st.error("Failed to add rule. The domain may already exist.")

st.markdown("---")

# --- List rules ---
PAGE_SIZE = 20

df = rules_controller.get_rules_dataframe()
if df.empty:
    st.info("The URL registry is currently empty.")
    st.stop()

list_type_filter = st.radio("Filter List Type", ["All", "Blacklist", "Whitelist"], horizontal=True)
filter_map = {"Blacklist": "BLACKLIST", "Whitelist": "WHITELIST"}
if list_type_filter != "All":
    df = df[df["ListType"] == filter_map[list_type_filter]].reset_index(drop=True)

search_query = st.text_input("Search", placeholder="Search by domain or added by...")
df = search_dataframe(df, search_query)

if "rules_page" not in st.session_state:
    st.session_state["rules_page"] = 0

total = len(df)
page = st.session_state["rules_page"]
start = page * PAGE_SIZE
end = min(start + PAGE_SIZE, total)

if total == 0:
    st.info("No rules found.")
    st.stop()

page_df = df.iloc[start:end].reset_index(drop=True)

# Display table with a delete button per row
col_headers = st.columns([2, 2, 3, 2, 1])
for col, label in zip(col_headers, ["List Type", "Domain", "Added By", "Created At", "Action"]):
    col.markdown(f"**{label}**")

for _, row in page_df.iterrows():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
    c1.write(row["ListType"])
    c2.write(row["URLDomain"])
    c3.write(row.get("AddedBy", "—"))
    c4.write(str(row["CreatedAt"])[:10] if row.get("CreatedAt") else "—")
    if c5.button("Delete", key=f"del_{row['RuleID']}"):
        if api_client.delete_url_rule(int(row["RuleID"])):
            api_client.log_action(current_user["user_id"], "URL Rule", f"Removed {row['URLDomain']} from {row['ListType']}")
            st.success(f"Removed {row['URLDomain']}.")
            st.rerun()
        else:
            st.error("Failed to delete rule.")

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
