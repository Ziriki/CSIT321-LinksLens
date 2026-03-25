import pandas as pd
from models import api_client


def get_audit_dataframe():
    raw_data = api_client.fetch_action_history()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)

    # Backend now returns FullName directly via JOIN
    df.rename(columns={"FullName": "User"}, inplace=True)

    return df[["LogID", "Timestamp", "User", "ActionType", "Action"]].sort_values(
        by="LogID", ascending=False
    )
