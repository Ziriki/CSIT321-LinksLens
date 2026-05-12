import pandas as pd
from models import api_client


############################################
# This function is to retrieve all URL rules from the backend and return
# them as a display-ready DataFrame with columns for RuleID, ListType,
# URLDomain, AddedBy, and CreatedAt.
############################################
def get_rules_dataframe():
    raw_data = api_client.fetch_url_rules()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)

    # Rename AddedByFullName to AddedBy for display and drop the raw int AddedBy column
    df.drop(columns=["AddedBy"], inplace=True, errors="ignore")
    df.rename(columns={"AddedByFullName": "AddedBy"}, inplace=True)

    return df[["RuleID", "ListType", "URLDomain", "AddedBy", "CreatedAt"]]


############################################
# This function is to add a domain to the blacklist or whitelist and
# log the action. Returns True on success.
############################################
def add_rule(domain: str, list_type: str, current_user_id: int) -> bool:
    success = api_client.create_url_rule(domain, list_type, current_user_id)
    if success:
        api_client.log_action(current_user_id, "URL Rule", f"Set {domain} to {list_type}")
    return success


############################################
# This function is to remove a URL rule by ID and log the action.
# Returns True on success.
############################################
def remove_rule(rule_id: int, domain: str, list_type: str, current_user_id: int) -> bool:
    success = api_client.delete_url_rule(rule_id)
    if success:
        api_client.log_action(current_user_id, "URL Rule", f"Removed {domain} from {list_type}")
    return success

