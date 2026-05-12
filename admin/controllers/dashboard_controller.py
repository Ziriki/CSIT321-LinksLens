from models import api_client


############################################
# This function is to retrieve system health data from the backend
# and return the raw response dict, or None on failure.
############################################
def get_system_health() -> dict | None:
    return api_client.fetch_system_health()
