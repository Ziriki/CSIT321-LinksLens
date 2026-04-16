import math
import streamlit as st
import pandas as pd
from typing import Any


def render_pagination(state_key: str, total: int, page_size: int = 20) -> tuple:
    """Render prev/next pagination controls and return (start, end) for slicing a dataframe."""
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


def search_dataframe(df: pd.DataFrame, query: str, columns: list = None) -> pd.DataFrame:
    """Apply case-insensitive search filter to a DataFrame."""
    if not query:
        return df
    search_cols = df[columns] if columns else df
    mask = search_cols.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
    return df[mask].reset_index(drop=True)


def render_ssl_expander(ssl: dict[str, Any]) -> None:
    """Render an SSL certificate details expander."""
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


def render_redirect_chain_expander(redirect_chain: list) -> None:
    """Render a redirect chain expander."""
    if not redirect_chain:
        return
    hops = len(redirect_chain)
    with st.expander(f"Redirect Chain ({hops} hop{'s' if hops != 1 else ''})"):
        for i, url in enumerate(redirect_chain, 1):
            st.markdown(f"{i}. `{url}`")


def render_script_analysis_expander(sa: dict[str, Any]) -> None:
    """Render a script analysis expander."""
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


def render_homograph_expander(ha: dict[str, Any]) -> None:
    """Render a homograph/IDN risk expander."""
    if not ha or not ha.get("is_homograph"):
        return
    with st.expander("⚠️ IDN Homograph Risk Detected"):
        st.error(ha.get("details", "Homograph risk detected."))
        if ha.get("confusable_chars"):
            st.markdown(f"**Confusable Characters:** `{'`, `'.join(ha['confusable_chars'])}`")
        if ha.get("mixed_scripts"):
            st.markdown(f"**Mixed Scripts:** {', '.join(ha['mixed_scripts'])}")
        st.markdown(f"**Risk Score:** {ha.get('risk_score', 0)}")
