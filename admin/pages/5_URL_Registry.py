import streamlit as st
from controllers import auth_controller, rules_controller
from utils import search_dataframe, render_pagination

current_user = auth_controller.require_role(1, 2)

st.title("URL Registry")

with st.expander("Submit a URL / Domain to Blacklist / Whitelist", expanded=False):
    with st.form("add_rule_form", clear_on_submit=True):
        domain = st.text_input("URL / Domain", placeholder="e.g. example.com")
        list_type = st.radio("List Type", ["BLACKLIST", "WHITELIST"], horizontal=True)
        submitted = st.form_submit_button("Submit")

    if submitted:
        domain = domain.strip().lower()
        if not domain:
            st.warning("Please enter a URL / domain.")
        else:
            if rules_controller.add_rule(domain, list_type, current_user["user_id"]):
                st.session_state["url_registry_toast"] = f"{domain} is now in the {list_type}."
                st.rerun()
            else:
                st.error(f"{domain} is already in the {list_type}.")

if toast := st.session_state.pop("url_registry_toast", None):
    st.success(toast)

st.markdown("---")

PAGE_SIZE = 20

df = rules_controller.get_rules_dataframe()
if df.empty:
    st.info("The URL registry is currently empty.")
    st.stop()

list_type_filter = st.radio("Filter List Type", ["All", "Blacklist", "Whitelist"], horizontal=True)
filter_map = {"Blacklist": "BLACKLIST", "Whitelist": "WHITELIST"}
if list_type_filter != "All":
    df = df[df["ListType"] == filter_map[list_type_filter]].reset_index(drop=True)

search_query = st.text_input("Search", placeholder="Search by URL / domain or added by...")
df = search_dataframe(df, search_query)

total = len(df)
if total == 0:
    st.info("No rules found.")
    st.stop()

start, end = render_pagination("rules_page", total, PAGE_SIZE)
page_df = df.iloc[start:end].reset_index(drop=True)

col_headers = st.columns([2, 2, 3, 2, 1])
for col, label in zip(col_headers, ["List Type", "URL / Domain", "Added By", "Created At", "Action"]):
    col.markdown(f"**{label}**")

for _, row in page_df.iterrows():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
    c1.write(row["ListType"])
    c2.write(row["URLDomain"])
    c3.write(row.get("AddedBy", "—"))
    c4.write(str(row["CreatedAt"])[:10] if row.get("CreatedAt") else "—")
    if c5.button("Delete", key=f"del_{row['RuleID']}"):
        if rules_controller.remove_rule(int(row["RuleID"]), row["URLDomain"], row["ListType"], current_user["user_id"]):
            st.success(f"Removed {row['URLDomain']}.")
            st.rerun()
        else:
            st.error("Failed to delete rule.")

