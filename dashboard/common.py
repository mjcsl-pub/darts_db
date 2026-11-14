"""Helpers shared by the per-game dashboard pages."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PERIODS = {"Game": None, "Week": "W", "Month": "M", "Quarter": "Q", "Year": "Y"}


def show(fig: go.Figure) -> None:
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), legend_title_text="")
    st.plotly_chart(fig, width="stretch")


def game_filters(df: pd.DataFrame, key: str, default_period: str = "Game"
                 ) -> tuple[pd.DataFrame, str, int]:
    """Sidebar date / profile / grouping filters. Returns (filtered df, period, window)."""
    sb = st.sidebar
    dmin, dmax = df["created_at"].min().date(), df["created_at"].max().date()
    rng = sb.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax, key=f"{key}_dates")
    start, end = (rng[0], rng[1]) if isinstance(rng, (tuple, list)) and len(rng) == 2 else (dmin, dmax)
    profiles = sorted(df["profile"].unique())
    sel = sb.multiselect("Profile", profiles, default=profiles, key=f"{key}_profiles")
    period = sb.selectbox("Group by", list(PERIODS), index=list(PERIODS).index(default_period),
                          key=f"{key}_period")
    window = sb.slider("Rolling window (games)", 1, 50, 10, key=f"{key}_window") if period == "Game" else 0
    d = df["created_at"].dt.date
    out = df[(d >= start) & (d <= end) & df["profile"].isin(sel)].copy()
    return out.sort_values(["created_at", "game_id"]).reset_index(drop=True), period, window


def period_start(s: pd.Series, period: str) -> pd.Series:
    return s.dt.to_period(PERIODS[period] or "M").dt.start_time


def game_picker(df: pd.DataFrame, label_fn, key: str):
    """Select one game (latest 500), newest first. Returns the game_id."""
    recent = df.sort_values("created_at", ascending=False).head(500)
    labels = {r.game_id: label_fn(r) for r in recent.itertuples()}
    return st.selectbox("Show details for game (latest 500)", list(labels),
                        format_func=lambda i: labels[i], key=key)
