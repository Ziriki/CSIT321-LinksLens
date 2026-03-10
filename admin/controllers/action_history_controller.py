import pandas as pd
from models import api_client


def get_audit_dataframe():
    raw_data = api_client.fetch_action_history()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)

    # Replace UserID with user name/email
    users = api_client.fetch_all_users()
    user_map = {u["UserID"]: u["EmailAddress"] for u in users}
    df["User"] = df["UserID"].map(user_map).fillna("Unknown")

    return df[["LogID", "Timestamp", "User", "ActionType", "Action"]].sort_values(
        by="LogID", ascending=False
    )
