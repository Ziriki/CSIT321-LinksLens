import pandas as pd
from models import api_client


############################################
# This function is to retrieve all audit log entries from the backend
# and return them as a display-ready DataFrame, sorted by LogID
# descending so the most recent actions appear first.
############################################
def get_audit_dataframe():
    raw_data = api_client.fetch_action_history()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)

    df.rename(columns={"FullName": "User"}, inplace=True)

    return df[["LogID", "Timestamp", "User", "ActionType", "Action"]].sort_values(
        by="LogID", ascending=False
    )
