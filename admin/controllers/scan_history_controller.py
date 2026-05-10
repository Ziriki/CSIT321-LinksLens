import streamlit as st
from models import api_client


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
