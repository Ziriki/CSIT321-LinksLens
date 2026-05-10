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

    # Rename AddedByFullName → AddedBy for display; drop the raw int AddedBy column
    df.drop(columns=["AddedBy"], inplace=True, errors="ignore")
    df.rename(columns={"AddedByFullName": "AddedBy"}, inplace=True)

    return df[["RuleID", "ListType", "URLDomain", "AddedBy", "CreatedAt"]]
