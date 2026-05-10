import math
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from typing import Any


_SCROLL_JS = (
    "<script>setTimeout(function(){"
    "var el=window.parent.document.querySelector('[data-testid=\"stMain\"]')"
    "||window.parent.document.querySelector('section.main')"
    "||window.parent.document.documentElement;"
    "el.scrollTo({top:el.scrollHeight,behavior:'smooth'});"
    "},500);</script>"
)


############################################
# This function is to smooth-scroll the Streamlit main panel to the
# bottom, but only once per new selection — not on every rerun. The
# state_key must be tied to the selected item's ID so the scroll only
# fires on the transition from no-selection to a new selection.
############################################
def scroll_to_bottom(state_key: str) -> None:
    if st.session_state.get("_scroll_key") != state_key:
        st.session_state["_scroll_key"] = state_key
        components.html(_SCROLL_JS, height=0)


############################################
# This function is to render Prev/Next pagination controls and return
# (start, end) index values for slicing a DataFrame.
############################################
def render_pagination(state_key: str, total: int, page_size: int = 20) -> tuple:
    if state_key not in st.session_state:
        st.session_state[state_key] = 0
    page = st.session_state[state_key]
    start = page * page_size
    end = min(start + page_size, total)

    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("← Prev", disabled=(page == 0), key=f"{state_key}_prev"):
            st.session_state[state_key] = max(0, page - 1)
            st.rerun()
    with col_info:
        st.markdown(f"Showing **{start + 1}–{end}** of {total} (Page {page + 1})")
    with col_next:
        if st.button("Next →", disabled=(end >= total), key=f"{state_key}_next"):
            st.session_state[state_key] = page + 1
            st.rerun()

    return start, end


############################################
# This function is to filter a DataFrame using a case-insensitive
# keyword search across all columns, or a specified subset of columns.
############################################
def search_dataframe(df: pd.DataFrame, query: str, columns: list = None) -> pd.DataFrame:
    if not query:
        return df
    search_cols = df[columns] if columns else df
    mask = search_cols.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
    return df[mask].reset_index(drop=True)


# Hex color codes mapped to each scan status for consistent UI styling
_STATUS_COLORS: dict[str, str] = {
    "MALICIOUS": "#dc2626",   # red
    "SUSPICIOUS": "#d97706",  # amber
    "SAFE": "#16a34a",        # green
    "UNAVAILABLE": "#6b7280", # grey
}


############################################
# This function is to return the hex color code for a given scan status
# string, defaulting to grey if the status is unrecognised.
############################################
def get_status_color(status: str) -> str:
    return _STATUS_COLORS.get(status, "#6b7280")  # default = grey


############################################
# This function is to render SSL certificate details inside a
# collapsible expander.
############################################
def render_ssl_expander(ssl: dict[str, Any]) -> None:
    if not ssl:
        return
    with st.expander("SSL Certificate"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Issuer:** {ssl.get('issuer', 'N/A')}")
            st.markdown(f"**Subject:** {ssl.get('subject') or 'N/A'}")
        with col2:
            st.markdown(f"**Valid From:** {ssl.get('valid_from') or 'N/A'}")
            st.markdown(f"**Valid Until:** {ssl.get('valid_to') or 'N/A'}")
            st.markdown(f"**Protocol:** {ssl.get('protocol', 'N/A')}")


############################################
# This function is to render the full redirect chain inside a
# collapsible expander, showing each hop as a numbered list.
############################################
def render_redirect_chain_expander(redirect_chain: list) -> None:
    if not redirect_chain:
        return
    hops = len(redirect_chain)
    with st.expander(f"Redirect Chain ({hops} hop{'s' if hops != 1 else ''})"):
        for i, url in enumerate(redirect_chain, 1):
            st.markdown(f"{i}. `{url}`")


############################################
# This function is to render script analysis metrics (totals, risk score,
# ad scripts, tech stack, malicious scripts, crypto miners, suspicious
# patterns) inside a collapsible expander.
############################################
def render_script_analysis_expander(sa: dict[str, Any]) -> None:
    if not sa:
        return
    with st.expander("Script Analysis"):
        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1:
            st.metric("Total Scripts", sa.get("total", 0))
        with s_col2:
            st.metric("Trusted CDN", sa.get("trusted_count", 0))
        with s_col3:
            st.metric("Script Risk Score", f"{sa.get('script_risk_score', 0)}/100")

        s_col4, s_col5 = st.columns(2)
        with s_col4:
            ad_label = f"{sa.get('ad_count', 0)}{' — ad-heavy' if sa.get('ad_heavy') else ''}"
            st.markdown(f"**Ad Scripts:** {ad_label}")
        with s_col5:
            tech = sa.get("tech_stack", [])
            if tech:
                st.markdown(f"**Technologies:** {', '.join(t.get('name', t) if isinstance(t, dict) else t for t in tech)}")

        if sa.get("malicious_scripts"):
            st.error(f"**Malicious Scripts:** {', '.join(sa['malicious_scripts'])}")
        if sa.get("crypto_miners"):
            st.error(f"**Crypto Miners:** {', '.join(sa['crypto_miners'])}")
        if sa.get("suspicious_patterns"):
            patterns = [p.get("reason", str(p)) if isinstance(p, dict) else p for p in sa["suspicious_patterns"]]
            st.warning(f"**Suspicious Patterns:** {', '.join(patterns)}")


############################################
# This function is to render IDN homograph risk details inside a
# collapsible expander. Only shown when the scan flagged a homograph attack.
############################################
def render_homograph_expander(ha: dict[str, Any]) -> None:
    if not ha or not ha.get("is_homograph"):
        return
    with st.expander("IDN Homograph Risk Detected"):
        st.error(ha.get("details", "Homograph risk detected."))
        if ha.get("confusable_chars"):
            st.markdown(f"**Confusable Characters:** `{'`, `'.join(ha['confusable_chars'])}`")
        if ha.get("mixed_scripts"):
            st.markdown(f"**Mixed Scripts:** {', '.join(ha['mixed_scripts'])}")
        st.markdown(f"**Risk Score:** {ha.get('risk_score', 0)}")
