import streamlit as st
import pandas as pd


def search_dataframe(df: pd.DataFrame, query: str, columns: list = None) -> pd.DataFrame:
    """Apply case-insensitive search filter to a DataFrame."""
    if not query:
        return df
    search_cols = df[columns] if columns else df
    mask = search_cols.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
    return df[mask].reset_index(drop=True)
