# controllers/rules_controller.py
import pandas as pd
from models import api_client

def get_rules_dataframe():
    raw_data = api_client.fetch_url_rules()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)

    # Backend now returns AddedByFullName directly via JOIN
    df.drop(columns=["AddedBy"], inplace=True, errors="ignore")
    df.rename(columns={"AddedByFullName": "AddedBy"}, inplace=True)

    return df[["RuleID", "ListType", "URLDomain", "AddedBy", "CreatedAt"]]
