"""Catch 40 page: checkout practice (40 targets, 6 darts each) tracked over time."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import game_filters, game_picker, period_start, show
from data import load_catch40, source_picker


def summarise(g: pd.DataFrame) -> pd.Series:
    co = g["checkouts"].sum()
    return pd.Series({
        "games": len(g),
        "avg_points": g["points"].mean(),
        "best_points": g["points"].max(),
        "avg_checkouts": g["checkouts"].mean(),
        "checkout_pct": co / g["targets"].sum() * 100 if g["targets"].sum() else float("nan"),
        "darts_per_co": g["co_darts"].sum() / co if co else float("nan"),
        "co2": g["co2"].mean(), "co3": g["co3"].mean(), "co4_6": g["co4_6"].mean(),
    })


def kpis(g: pd.DataFrame) -> None:
    s = summarise(g)
    c = st.columns(7)
    c[0].metric("Games", f"{s.games:,.0f}")
    c[1].metric("Avg points", f"{s.avg_points:.1f}")
    c[2].metric("Best points", f"{s.best_points:.0f}")
    c[3].metric("Avg checkouts", f"{s.avg_checkouts:.1f} / 40")
    c[4].metric("Checkout %", f"{s.checkout_pct:.1f}%", help="Targets checked out within 6 darts")
    c[5].metric("Darts per checkout", f"{s.darts_per_co:.2f}")
    c[6].metric("2 / 3 / 4-6 darts", f"{s.co2:.1f} / {s.co3:.1f} / {s.co4_6:.1f}",
                help="Average checkouts per game by darts used (3, 2 and 1 points)")


def trends(g: pd.DataFrame, period: str, window: int) -> None:
    if period == "Game":
        c1, c2 = st.columns(2)
        for col, y, title in ((c1, "points", "Points per game"), (c2, "checkouts", "Checkouts per game")):
            fig = go.Figure()
            fig.add_scatter(x=g["created_at"], y=g[y], mode="markers", name="Game",
                            marker=dict(size=7, opacity=0.5),
                            hovertemplate="%{x|%Y-%m-%d %H:%M}: %{y}<extra></extra>")
            fig.add_scatter(x=g["created_at"], y=g[y].rolling(window, min_periods=1).mean(), mode="lines",
                            name=f"Average (last {window})")
            fig.update_layout(title=title)
            with col:
                show(fig)
        m = g.melt(id_vars=["created_at"], value_vars=["co2", "co3", "co4_6"], var_name="darts", value_name="n")
        m["darts"] = m["darts"].map({"co2": "2 darts (3 pts)", "co3": "3 darts (2 pts)", "co4_6": "4-6 darts (1 pt)"})
        show(px.bar(m, x="created_at", y="n", color="darts", title="Checkouts per game by darts used",
                    labels={"created_at": "", "n": "Checkouts"}))
        return

    p = g.groupby(period_start(g["created_at"], period)).apply(summarise).reset_index()
    p = p.rename(columns={"created_at": "period"})
    c1, c2 = st.columns(2)
    with c1:
        show(px.line(p, x="period", y="avg_points", markers=True, title=f"Avg points per {period.lower()}",
                     labels={"period": "", "avg_points": "Points"}, hover_data=["games"]))
    with c2:
        show(px.line(p, x="period", y="checkout_pct", markers=True, title=f"Checkout % per {period.lower()}",
                     labels={"period": "", "checkout_pct": "%"}, hover_data=["games"]))
    c3, c4 = st.columns(2)
    with c3:
        m = p.melt(id_vars="period", value_vars=["co2", "co3", "co4_6"], var_name="darts", value_name="n")
        m["darts"] = m["darts"].map({"co2": "2 darts", "co3": "3 darts", "co4_6": "4-6 darts"})
        show(px.bar(m, x="period", y="n", color="darts", title=f"Avg checkouts per game by darts used",
                    labels={"period": "", "n": "Checkouts per game"}))
    with c4:
        show(px.bar(p, x="period", y="games", title=f"Games per {period.lower()}", labels={"period": "", "games": "Games"}))


def per_target(t: pd.DataFrame) -> None:
    a = t.groupby("target").agg(attempts=("checkout", "size"), checkouts=("checkout", "sum"),
                                points=("points", "sum")).reset_index()
    darts = t[t["checkout"] == 1].groupby("target")["darts"].mean().rename("avg_darts")
    a = a.merge(darts, left_on="target", right_index=True, how="left")
    a["checkout_pct"] = a["checkouts"] / a["attempts"] * 100
    fig = px.bar(a, x="target", y="checkout_pct", color="avg_darts", color_continuous_scale="RdYlGn_r",
                 range_color=(2, 6), hover_data={"attempts": True, "checkouts": True, "avg_darts": ":.1f"},
                 title="Checkout % per target", labels={"target": "Target", "checkout_pct": "%",
                                                        "avg_darts": "Avg darts"})
    fig.update_xaxes(dtick=1 if a["target"].nunique() <= 40 else 5)
    show(fig)
    st.caption("Colour shows the average darts needed when the target was checked out.")


def game_detail(g: pd.DataFrame, t: pd.DataFrame) -> None:
    st.subheader("Games")
    st.dataframe(
        g.sort_values("created_at", ascending=False)[
            ["game_id", "created_at", "profile", "mode_name", "points", "checkouts", "co2", "co3", "co4_6"]],
        hide_index=True, height=300,
        column_config={"game_id": "Game", "created_at": st.column_config.DatetimeColumn("Played", format="YYYY-MM-DD HH:mm"),
                       "mode_name": "Targets", "co2": "2-dart", "co3": "3-dart", "co4_6": "4-6-dart"})
    gid = game_picker(g, lambda r: f"{r.created_at:%Y-%m-%d %H:%M}  {r.points} pts  {r.checkouts} checkouts", "catch_game")
    tg = t[t["game_id"] == gid]
    st.dataframe(tg[["target", "darts", "checkout", "points"]], hide_index=True, height=300,
                 column_config={"target": "Target", "darts": "Darts used", "checkout": "Checked out"})


def render() -> None:
    st.title("Catch 40")
    path = source_picker()
    games, targets = load_catch40(str(path), path.stat().st_mtime)
    if games.empty:
        st.info("No Catch 40 games in this database.")
        return
    modes = games["mode_name"].value_counts().index.tolist()  # most played first
    mode = st.sidebar.radio("Targets", modes, horizontal=True, key="catch_mode",
                            help="Points aren't comparable between target ranges")
    g, period, window = game_filters(games[games["mode_name"] == mode], "catch")
    if g.empty:
        st.warning("No games match the filters.")
        return
    t = targets[targets["game_id"].isin(g["game_id"])]
    kpis(g)
    trends(g, period, window)
    per_target(t)
    game_detail(g, t)
    st.caption("Each target gets 6 darts. Points: checkout in 2 darts = 3, in 3 darts = 2, in 4-6 darts = 1.")
