import html
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from controllers import auth_controller, threat_intelligence_controller
from utils import get_status_color
# ISO-2 country code → (latitude, longitude) centroids for major countries
COUNTRY_COORDS = {
    "AF": (33.94, 67.71), "AL": (41.15, 20.17), "DZ": (28.03, 1.66),
    "AO": (-11.20, 17.87), "AR": (-38.42, -63.62), "AU": (-25.27, 133.78),
    "AT": (47.52, 14.55), "AZ": (40.14, 47.58), "BD": (23.68, 90.36),
    "BE": (50.50, 4.47), "BJ": (9.31, 2.32), "BO": (-16.29, -63.59),
    "BR": (-14.24, -51.93), "BG": (42.73, 25.49), "KH": (12.57, 104.99),
    "CA": (56.13, -106.35), "CL": (-35.68, -71.54), "CN": (35.86, 104.19),
    "CO": (4.57, -74.30), "CD": (-4.04, 21.76), "CR": (9.75, -83.75),
    "HR": (45.10, 15.20), "CZ": (49.82, 15.47), "DK": (56.26, 9.50),
    "EC": (-1.83, -78.18), "EG": (26.82, 30.80), "ET": (9.15, 40.49),
    "FI": (61.92, 25.75), "FR": (46.23, 2.21), "GH": (7.95, -1.02),
    "DE": (51.17, 10.45), "GR": (39.07, 21.82), "GT": (15.78, -90.23),
    "HN": (15.20, -86.24), "HK": (22.40, 114.11), "HU": (47.16, 19.50),
    "IN": (20.59, 78.96), "ID": (-0.79, 113.92), "IR": (32.43, 53.69),
    "IQ": (33.22, 43.68), "IE": (53.41, -8.24), "IL": (31.05, 34.85),
    "IT": (41.87, 12.57), "JP": (36.20, 138.25), "JO": (30.59, 36.24),
    "KZ": (48.02, 66.92), "KE": (-0.02, 37.91), "KP": (40.34, 127.51),
    "KR": (35.91, 127.77), "KW": (29.31, 47.48), "LB": (33.85, 35.86),
    "LY": (26.34, 17.23), "MY": (4.21, 108.96), "MX": (23.63, -102.55),
    "MA": (31.79, -7.09), "MZ": (-18.67, 35.53), "MM": (21.92, 95.96),
    "NP": (28.39, 84.12), "NL": (52.13, 5.29), "NZ": (-40.90, 174.89),
    "NG": (9.08, 8.68), "NO": (60.47, 8.47), "PK": (30.38, 69.35),
    "PA": (8.54, -80.78), "PY": (-23.44, -58.44), "PE": (-9.19, -75.02),
    "PH": (12.88, 121.77), "PL": (51.92, 19.15), "PT": (39.40, -8.22),
    "QA": (25.35, 51.18), "RO": (45.94, 24.97), "RU": (61.52, 105.32),
    "SA": (23.89, 45.08), "SN": (14.50, -14.45), "ZA": (-30.56, 22.94),
    "ES": (40.46, -3.75), "LK": (7.87, 80.77), "SD": (12.86, 30.22),
    "SE": (60.13, 18.64), "CH": (46.82, 8.23), "SY": (34.80, 38.99),
    "TW": (23.70, 121.00), "TZ": (-6.37, 34.89), "TH": (15.87, 100.99),
    "TN": (33.89, 9.54), "TR": (38.96, 35.24), "UA": (48.38, 31.17),
    "AE": (23.42, 53.85), "GB": (55.38, -3.44), "US": (37.09, -95.71),
    "UY": (-32.52, -55.77), "UZ": (41.38, 64.59), "VE": (6.42, -66.59),
    "VN": (14.06, 108.28), "YE": (15.55, 48.52), "ZM": (-13.13, 27.85),
    "ZW": (-19.02, 29.15),
}

auth_controller.require_role(1, 2)

st.title("Threat Intelligence")

# Fetch data upfront so both sections can use it
stats = threat_intelligence_controller.get_threat_stats()
threats = threat_intelligence_controller.get_recent_threats()

# ── Recent Threats Table ──────────────────────────────────────────────────────
# Rendered first so the selection is a local variable available to the map below.

st.subheader("Recent Threats")

selected_threat = None  # dict of the selected row, or None

if not threats:
    st.info("No recent threats to display.")
else:
    df = pd.DataFrame(threats)
    df.columns = ["URL", "Status", "Location", "Scanned At"]

    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = event.selection.rows if event.selection else []
    if selected_rows:
        selected_threat = threats[selected_rows[0]]

# ── Selected URL info ─────────────────────────────────────────────────────────

if selected_threat:
    status_color = get_status_color(selected_threat["status"])
    safe_url      = html.escape(selected_threat["url"] or "")
    safe_location = html.escape(selected_threat["location"] or "Unknown")
    safe_time     = html.escape(str(selected_threat["scanned_at"] or "N/A"))
    safe_status   = html.escape(selected_threat["status"] or "")
    st.markdown(
        f"**Selected:** `{safe_url}` · "
        f"<span style='color:{status_color};font-weight:600'>{safe_status}</span> · "
        f"{safe_location} · {safe_time}",
        unsafe_allow_html=True,
    )

# ── Global Threat Heatmap ─────────────────────────────────────────────────────

st.subheader("Global Threat Heatmap")

if not stats and not threats:
    st.info("No threat data available yet.")
else:
    selected_location = selected_threat.get("location") if selected_threat else None
    pin_coords = COUNTRY_COORDS.get(selected_location) if selected_location else None

    map_center = pin_coords if pin_coords else (20, 0)
    map_zoom = 4 if pin_coords else 2

    world_map = folium.Map(location=map_center, zoom_start=map_zoom, tiles="CartoDB positron")

    if stats:
        max_total = max((s.get("total", 0) for s in stats), default=1)
        for entry in stats:
            location = entry.get("location")
            if not location or location not in COUNTRY_COORDS:
                continue
            lat, lon = COUNTRY_COORDS[location]
            total = entry.get("total", 0)
            malicious = entry.get("malicious", 0)
            suspicious = entry.get("suspicious", 0)

            radius = max(5, min(30, int(5 + 25 * (total / max_total))))
            severity_ratio = malicious / total if total else 0
            color = "red" if severity_ratio >= 0.5 else "orange"

            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.6,
                popup=folium.Popup(
                    f"<b>{html.escape(location)}</b><br>Malicious: {malicious}<br>Suspicious: {suspicious}<br>Total: {total}",
                    max_width=200,
                ),
            ).add_to(world_map)

    if pin_coords:
        folium.Marker(
            location=pin_coords,
            popup=folium.Popup(
                f"<b>{safe_url}</b><br>{safe_status}<br>{safe_location}",
                max_width=300,
            ),
            icon=folium.Icon(color="purple", icon="map-marker"),
        ).add_to(world_map)

    st_folium(world_map, width=None, height=450, returned_objects=[])
