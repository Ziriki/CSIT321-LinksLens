import pandas as pd
from models import api_client


############################################
# This function is to retrieve all app feedback submissions from the
# backend and return them as a display-ready DataFrame.
############################################
def get_feedback_dataframe():
    raw_data = api_client.fetch_app_feedback()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)

    df.rename(columns={"FullName": "User"}, inplace=True)

    return df[["FeedbackID", "User", "Feedback", "CreatedAt"]]
