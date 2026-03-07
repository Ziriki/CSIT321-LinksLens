import pandas as pd
from models import api_client


def get_audit_dataframe():
    raw_data = api_client.fetch_action_history()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)
    return df[["LogID", "Timestamp", "UserID", "ActionType", "Action"]].sort_values(
        by="Timestamp", ascending=False
    )
