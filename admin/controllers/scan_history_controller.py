import streamlit as st
from models import api_client


############################################
# This function is to submit a URL to the scan pipeline and return the
# result dict, or None on failure.
############################################
def run_scan(url: str) -> dict | None:
    return api_client.scan_url(url)


############################################
# This function is to retrieve a paginated and filtered list of scan
# records from the backend.
############################################
def get_scan_list(skip: int, limit: int, search: str = None, status_indicator: str = None) -> list:
    return api_client.fetch_scan_list(skip=skip, limit=limit, search=search, status_indicator=status_indicator)


############################################
# This function is to retrieve the full scan details for a given scan ID
# and show an error message if the record is not found.
############################################
def get_forensic_data(scan_id: int):
    if not scan_id:
        return None
    data = api_client.fetch_scan_details(scan_id)
    if not data:
        st.error(f"Scan ID {scan_id} not found.")
    return data
