# controllers/scan_controller.py
from models import api_client
import streamlit as st

def get_forensic_data(scan_id: int):
    if not scan_id: return None
    data = api_client.fetch_scan_details(scan_id)
    if not data:
        st.error(f"Scan ID {scan_id} not found.")
    return data