# controllers/rules_controller.py
import pandas as pd
from models import api_client

def get_rules_dataframe():
    raw_data = api_client.fetch_url_rules()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)

    # Replace AddedBy (UserID) with email
    users = api_client.fetch_all_users()
    user_map = {u["UserID"]: u["EmailAddress"] for u in users}
    df["AddedBy"] = df["AddedBy"].map(user_map).fillna("Unknown")

    return df[["RuleID", "ListType", "URLDomain", "AddedBy", "CreatedAt"]]
