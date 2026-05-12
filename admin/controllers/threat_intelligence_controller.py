from models import api_client


############################################
# This function is to retrieve aggregated threat statistics grouped
# by country for the heatmap.
############################################
def get_threat_stats() -> list:
    return api_client.fetch_threat_stats()


############################################
# This function is to retrieve the most recent malicious and suspicious
# scan records for the threat feed table.
############################################
def get_recent_threats() -> list:
    return api_client.fetch_recent_threats()
