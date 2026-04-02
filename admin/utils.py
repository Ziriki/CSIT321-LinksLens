import math
import streamlit as st
import pandas as pd


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
