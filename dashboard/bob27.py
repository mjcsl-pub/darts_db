"""Bob's 27 page: doubles practice tracked over time."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import game_filters, game_picker, period_start, show
from data import BOB_DOUBLES, load_bob27, source_picker


def summarise(g: pd.DataFrame) -> pd.Series:
    darts = g["darts"].sum()
    return pd.Series({
        "games": len(g),
        "completed": int(g["completed"].sum()),
        "avg_rounds": g["rounds"].mean(),
        "hit_pct": g["hits"].sum() / darts * 100 if darts else float("nan"),
        "best_score": g["score"].max(),
    })


def kpis(g: pd.DataFrame) -> None:
    s = summarise(g)
    best_rounds = g["rounds"].max()
    c = st.columns(6)
    c[0].metric("Games", f"{s.games:,.0f}")
    c[1].metric("Completed", f"{s.completed:.0f}", help="Survived all doubles and the bull with a score above 0")
    c[2].metric("Best score", f"{s.best_score:.0f}")
    c[3].metric("Avg doubles reached", f"{s.avg_rounds:.1f}", help="Targets played before the game ended (max 21)")
    c[4].metric("Most doubles reached", f"{best_rounds:.0f}")
    c[5].metric("Double hit %", f"{s.hit_pct:.1f}%", help="Doubles hit / darts thrown")


def trends(g: pd.DataFrame, period: str, window: int) -> None:
    if period == "Game":
        roll_rounds = g["rounds"].rolling(window, min_periods=1).mean()
        roll_hit = (g["hits"].rolling(window, min_periods=1).sum()
                    / g["darts"].rolling(window, min_periods=1).sum() * 100)
        fig = go.Figure()
        fig.add_scatter(x=g["created_at"], y=g["rounds"], mode="markers", name="Doubles reached",
                        marker=dict(size=6, opacity=0.45), customdata=g[["score", "last_target"]],
                        hovertemplate="%{x|%Y-%m-%d %H:%M}<br>%{y} doubles, ended on %{customdata[1]}"
                                      "<br>score %{customdata[0]}<extra></extra>")
        fig.add_scatter(x=g["created_at"], y=roll_rounds, mode="lines", name=f"Average (last {window})")
        fig.update_layout(title="Doubles reached per game", yaxis=dict(title="Doubles", range=[0, 22]))
        show(fig)
        c1, c2 = st.columns(2)
        with c1:
            show(px.line(x=g["created_at"], y=roll_hit, title=f"Double hit % (last {window} games)",
                         labels={"x": "", "y": "%"}))
        with c2:
            done = g[g["completed"]]
            if done.empty:
                st.info("No completed games in this selection.")
            else:
                show(px.scatter(done, x="created_at", y="score", title="Score of completed games",
                                labels={"created_at": "", "score": "Score"}))
        return

    p = g.groupby(period_start(g["created_at"], period)).apply(summarise).reset_index()
    p = p.rename(columns={"created_at": "period"})
    c1, c2 = st.columns(2)
    with c1:
        show(px.line(p, x="period", y="avg_rounds", markers=True, title=f"Avg doubles reached per {period.lower()}",
                     labels={"period": "", "avg_rounds": "Doubles"}, hover_data=["games"]))
    with c2:
        show(px.line(p, x="period", y="hit_pct", markers=True, title=f"Double hit % per {period.lower()}",
                     labels={"period": "", "hit_pct": "%"}, hover_data=["games"]))
    c3, c4 = st.columns(2)
    with c3:
        show(px.bar(p, x="period", y="games", title=f"Games per {period.lower()}", labels={"period": "", "games": "Games"}))
    with c4:
        show(px.line(p, x="period", y="best_score", markers=True, title=f"Best score per {period.lower()}",
                     labels={"period": "", "best_score": "Score"}))


def per_double(t: pd.DataFrame, period: str) -> None:
    agg = t.groupby("target").agg(darts=("darts", "sum"), hits=("hits", "sum")).reindex(BOB_DOUBLES).dropna()
    agg["hit_pct"] = agg["hits"] / agg["darts"] * 100
    show(px.bar(agg.reset_index(), x="target", y="hit_pct", title="Hit % per double",
                hover_data={"darts": True, "hits": True}, labels={"target": "", "hit_pct": "%"},
                category_orders={"target": BOB_DOUBLES}))
    st.caption("Later doubles have fewer darts because most games end early. Hover a bar to see the sample size.")

    by = "Year" if period == "Game" else period
    t = t.assign(period=period_start(t["created_at"], by).dt.strftime("%Y" if by == "Year" else "%Y-%m-%d"))
    h = t.groupby(["period", "target"]).agg(darts=("darts", "sum"), hits=("hits", "sum")).reset_index()
    h["hit_pct"] = h["hits"] / h["darts"] * 100
    piv = h.pivot(index="period", columns="target", values="hit_pct").reindex(columns=BOB_DOUBLES)
    n = h.pivot(index="period", columns="target", values="darts").reindex(columns=BOB_DOUBLES)
    fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index, customdata=n.values,
                               colorscale="RdYlGn", zmin=0, zmax=50, colorbar=dict(title="%"),
                               hovertemplate="%{y} %{x}: %{z:.0f}% of %{customdata} darts<extra></extra>"))
    fig.update_layout(title=f"Hit % per double by {by.lower()}", yaxis=dict(type="category"))
    show(fig)


def game_detail(g: pd.DataFrame, t: pd.DataFrame) -> None:
    st.subheader("Games")
    st.dataframe(
        g.sort_values("created_at", ascending=False)[
            ["game_id", "created_at", "profile", "score", "rounds", "last_target", "hits", "darts", "hit_pct",
             "completed", "easy_mode"]],
        hide_index=True, height=300,
        column_config={"game_id": "Game", "created_at": st.column_config.DatetimeColumn("Played", format="YYYY-MM-DD HH:mm"),
                       "rounds": "Doubles reached", "last_target": "Last double",
                       "hit_pct": st.column_config.NumberColumn("Hit %", format="%.1f"),
                       "easy_mode": "Easy mode"})
    gid = game_picker(g, lambda r: f"{r.created_at:%Y-%m-%d %H:%M}  score {r.score}  {r.rounds} doubles", "bob_game")
    tg = t[t["game_id"] == gid]
    c1, c2 = st.columns([2, 3])
    with c1:
        st.dataframe(tg[["target", "darts", "hits", "change", "score_after"]], hide_index=True,
                     column_config={"target": "Double", "change": "+/-", "score_after": "Score after"})
    with c2:
        y = pd.concat([pd.Series([27]), tg["score_after"]], ignore_index=True)
        x = ["Start"] + tg["target"].tolist()
        show(px.line(x=x, y=y, markers=True, title="Running score", labels={"x": "", "y": "Score"}))


def render() -> None:
    st.title("Bob's 27")
    path = source_picker()
    games, targets = load_bob27(str(path), path.stat().st_mtime)
    if games.empty:
        st.info("No Bob's 27 games in this database.")
        return
    g, period, window = game_filters(games, "bob")
    if g.empty:
        st.warning("No games match the filters.")
        return
    t = targets[targets["game_id"].isin(g["game_id"])]
    kpis(g)
    trends(g, period, window)
    per_double(t, period)
    game_detail(g, t)
    st.caption("Rules: start on 27, each hit adds the double's value, three misses subtract it, "
               "and the game ends at 0. Scores are rebuilt from the per-double rows and match the app.")
