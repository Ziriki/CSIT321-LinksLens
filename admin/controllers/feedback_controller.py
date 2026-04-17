import pandas as pd
from models import api_client


def get_feedback_dataframe():
    """Return app feedback submissions as a display-ready DataFrame."""
    raw_data = api_client.fetch_app_feedback()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)

    df.rename(columns={"FullName": "User"}, inplace=True)

    return df[["FeedbackID", "User", "Feedback", "CreatedAt"]]
