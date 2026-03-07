import pandas as pd
from models import api_client

def get_feedback_dataframe():
    raw_data = api_client.fetch_app_feedback()
    if not raw_data: return pd.DataFrame()
    return pd.DataFrame(raw_data)[["FeedbackID", "UserID", "Feedback", "CreatedAt"]]