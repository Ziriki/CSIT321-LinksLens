import pandas as pd
from models import api_client


def get_feedback_dataframe():
    raw_data = api_client.fetch_app_feedback()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)

    # Replace UserID with user name/email
    users = api_client.fetch_all_users()
    user_map = {u["UserID"]: u["EmailAddress"] for u in users}
    df["User"] = df["UserID"].map(user_map).fillna("Unknown")

    return df[["FeedbackID", "User", "Feedback", "CreatedAt"]]
