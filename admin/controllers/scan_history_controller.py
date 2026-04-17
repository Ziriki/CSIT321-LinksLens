import streamlit as st
from models import api_client


def get_forensic_data(scan_id: int):
    """Return full scan details for a given scan ID, or None if not found."""
    if not scan_id:
        return None
    data = api_client.fetch_scan_details(scan_id)
    if not data:
        st.error(f"Scan ID {scan_id} not found.")
    return data
