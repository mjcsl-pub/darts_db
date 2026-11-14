"""X01 page: track legs of one start score (e.g. 501) over time."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data import load_x01, source_picker

PERIODS = {"Leg": None, "Week": "W", "Month": "M", "Quarter": "Q", "Year": "Y"}


def show(fig: go.Figure) -> None:
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), legend_title_text="")
    st.plotly_chart(fig, width="stretch")


def weighted_avg(score: pd.Series, darts: pd.Series) -> float:
    d = darts.sum()
    return score.sum() / d * 3 if d else float("nan")


def summarise(df: pd.DataFrame) -> pd.Series:
    out = df[df["checked_out"]]
    dad = df["darts_at_double"].sum()
    vs_cpu = df[df["mode"] == "vs CPU"]
    return pd.Series({
        "legs": len(df),
        "avg3": weighted_avg(df["scored"], df["darts"]),
        "first9": weighted_avg(df["f9_score"], df["f9_darts"]),
        "checkout_pct": df["checked_out"].sum() / dad * 100 if dad else float("nan"),
        "darts_per_leg": out["darts"].mean() if len(out) else float("nan"),
        "checked_out": int(df["checked_out"].sum()),
        "n100": int(df["n100"].sum()),
        "n140": int(df["n140"].sum()),
        "n180": int(df["n180"].sum()),
        "win_pct": vs_cpu["win"].mean() * 100 if len(vs_cpu) else float("nan"),
    })


def filters(legs: pd.DataFrame) -> tuple[pd.DataFrame, str, int]:
    sb = st.sidebar
    dmin, dmax = legs["created_at"].min().date(), legs["created_at"].max().date()
    rng = sb.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
    start, end = (rng[0], rng[1]) if isinstance(rng, (tuple, list)) and len(rng) == 2 else (dmin, dmax)
    profiles = sorted(legs["profile"].unique())
    sel_profiles = sb.multiselect("Profile", profiles, default=profiles)
    modes = sorted(legs["mode"].unique())
    sel_modes = sb.multiselect("Mode", modes, default=modes,
                               help="Training legs or legs played against the CPU (challenge mode)")
    period = sb.selectbox("Group by", list(PERIODS), index=2)
    window = sb.slider("Rolling window (legs)", 1, 100, 20) if period == "Leg" else 0

    d = legs["created_at"].dt.date
    mask = (d >= start) & (d <= end) & legs["profile"].isin(sel_profiles) & legs["mode"].isin(sel_modes)
    return legs[mask].copy(), period, window


def by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    freq = PERIODS[period] or "M"
    key = df["created_at"].dt.to_period(freq).dt.start_time
    out = df.groupby(key).apply(summarise).reset_index()
    return out.rename(columns={"created_at": "period"})


def rolling(df: pd.DataFrame, window: int) -> pd.DataFrame:
    r = df[["created_at", "leg_id"]].copy()
    r["n"] = range(1, len(df) + 1)
    for name, s, d in (("avg3", "scored", "darts"), ("first9", "f9_score", "f9_darts")):
        r[name] = (df[s].rolling(window, min_periods=1).sum()
                   / df[d].rolling(window, min_periods=1).sum() * 3)
    dad = df["darts_at_double"].rolling(window, min_periods=1).sum()
    r["checkout_pct"] = df["checked_out"].astype(int).rolling(window, min_periods=1).sum() / dad * 100
    co = df["darts"].where(df["checked_out"])
    r["darts_per_leg"] = co.rolling(window, min_periods=1).mean()
    return r


def kpis(df: pd.DataFrame) -> None:
    s = summarise(df)
    best = df.loc[df["checked_out"], "darts"].min()
    hi_co = df["checkout_value"].max()
    cols = st.columns(8)
    cols[0].metric("Legs", f"{s.legs:,.0f}")
    cols[1].metric("3-dart avg", f"{s.avg3:.2f}")
    cols[2].metric("First-9 avg", f"{s.first9:.2f}")
    cols[3].metric("Checkout %", f"{s.checkout_pct:.1f}%", help="Checkouts / darts at double")
    cols[4].metric("Darts / leg", f"{s.darts_per_leg:.1f}", help="Average darts in checked-out legs")
    cols[5].metric("Best leg", f"{best:.0f} darts" if pd.notna(best) else "-")
    cols[6].metric("Highest checkout", f"{hi_co:.0f}" if pd.notna(hi_co) else "-")
    cols[7].metric("100+ / 140+ / 180", f"{s.n100:.0f} / {s.n140:.0f} / {s.n180:.0f}")


def trend_charts(df: pd.DataFrame, period: str, window: int) -> None:
    if period == "Leg":
        r = rolling(df, window)
        fig = go.Figure()
        fig.add_scatter(x=df["created_at"], y=df["avg3"], mode="markers", name="Leg average",
                        marker=dict(size=5, opacity=0.35),
                        customdata=df[["leg_id", "darts"]],
                        hovertemplate="%{x|%Y-%m-%d %H:%M}<br>avg %{y:.2f}<br>%{customdata[1]} darts"
                                      "<extra>leg %{customdata[0]}</extra>")
        fig.add_scatter(x=r["created_at"], y=r["avg3"], mode="lines", name=f"3-dart avg (last {window})")
        fig.add_scatter(x=r["created_at"], y=r["first9"], mode="lines", name=f"First-9 avg (last {window})",
                        line=dict(dash="dot"))
        fig.update_layout(title="Averages per leg", yaxis_title="Average")
        show(fig)

        c1, c2 = st.columns(2)
        with c1:
            show(px.line(r, x="created_at", y="checkout_pct", title=f"Checkout % (last {window} legs)",
                         labels={"created_at": "", "checkout_pct": "%"}))
        with c2:
            show(px.line(r, x="created_at", y="darts_per_leg",
                         title=f"Darts per checked-out leg (last {window} legs)",
                         labels={"created_at": "", "darts_per_leg": "Darts"}))
        return

    p = by_period(df, period)
    fig = go.Figure()
    fig.add_scatter(x=p["period"], y=p["avg3"], mode="lines+markers", name="3-dart avg",
                    customdata=p[["legs"]], hovertemplate="%{y:.2f} (%{customdata[0]} legs)")
    fig.add_scatter(x=p["period"], y=p["first9"], mode="lines+markers", name="First-9 avg",
                    line=dict(dash="dot"))
    fig.update_layout(title=f"Averages per {period.lower()}", yaxis_title="Average")
    show(fig)

    c1, c2 = st.columns(2)
    with c1:
        show(px.line(p, x="period", y="checkout_pct", markers=True, title=f"Checkout % per {period.lower()}",
                     labels={"period": "", "checkout_pct": "%"}))
    with c2:
        show(px.line(p, x="period", y="darts_per_leg", markers=True,
                     title=f"Darts per checked-out leg per {period.lower()}",
                     labels={"period": "", "darts_per_leg": "Darts"}))

    c3, c4 = st.columns(2)
    with c3:
        m = p.melt(id_vars="period", value_vars=["n100", "n140", "n180"], var_name="band", value_name="count")
        m["band"] = m["band"].map({"n100": "100-139", "n140": "140-179", "n180": "180"})
        show(px.bar(m, x="period", y="count", color="band", title=f"High scores per {period.lower()}",
                    labels={"period": "", "count": "Visits"}))
    with c4:
        show(px.bar(p, x="period", y="legs", title=f"Legs played per {period.lower()}",
                    labels={"period": "", "legs": "Legs"}))
    if p["win_pct"].notna().any():
        show(px.line(p, x="period", y="win_pct", markers=True,
                     title=f"Legs won vs CPU per {period.lower()}", labels={"period": "", "win_pct": "%"}))


def checkout_chart(df: pd.DataFrame) -> None:
    co = df["checkout_value"].dropna()
    if co.empty:
        return
    show(px.histogram(co, nbins=40, title="Checkout scores",
                      labels={"value": "Checkout", "count": "Times"}).update_layout(showlegend=False))


def leg_table(df: pd.DataFrame, visits: pd.DataFrame) -> None:
    st.subheader("Legs")
    t = df.sort_values("created_at", ascending=False)[[
        "leg_id", "created_at", "profile", "mode", "avg3", "first9", "darts", "checked_out",
        "checkout_value", "darts_at_double", "highest_visit", "n180", "win", "cpu_level"]]
    st.dataframe(
        t, hide_index=True, height=320,
        column_config={
            "leg_id": "Leg", "created_at": st.column_config.DatetimeColumn("Played", format="YYYY-MM-DD HH:mm"),
            "avg3": st.column_config.NumberColumn("3-dart avg", format="%.2f"),
            "first9": st.column_config.NumberColumn("First-9", format="%.2f"),
            "checked_out": "Checked out", "checkout_value": "Checkout", "darts_at_double": "Darts at double",
            "highest_visit": "High visit", "n180": "180s", "win": "Won vs CPU", "cpu_level": "CPU level",
        },
    )

    options = t["leg_id"].tolist()[:500]
    labels = {r.leg_id: f"{r.created_at:%Y-%m-%d %H:%M}  avg {r.avg3:.1f}  {r.darts} darts"
              for r in t.head(500).itertuples()}
    leg = st.selectbox("Show visits for leg (latest 500)", options, format_func=lambda i: labels[i])
    v = visits[visits["leg_id"] == leg]
    c1, c2 = st.columns([2, 3])
    with c1:
        st.dataframe(v[["round", "remaining", "score", "darts", "darts_at_double", "checkout"]],
                     hide_index=True,
                     column_config={"round": "Visit", "remaining": "Remaining before",
                                    "darts_at_double": "At double"})
    with c2:
        left = pd.concat([v["remaining"], (v["remaining"] - v["score"]).tail(1)], ignore_index=True)
        show(px.line(x=range(len(left)), y=left, markers=True, title="Remaining score",
                     labels={"x": "Visit", "y": "Remaining"}))


def render(start_score: int) -> None:
    st.title(f"{start_score}")
    path = source_picker()
    legs, visits = load_x01(str(path), path.stat().st_mtime, start_score)
    if legs.empty:
        st.info(f"No {start_score} legs in this database.")
        return
    df, period, window = filters(legs)
    if df.empty:
        st.warning("No legs match the filters.")
        return
    kpis(df)
    trend_charts(df, period, window)
    checkout_chart(df)
    leg_table(df, visits)
    st.caption("3-dart and first-9 averages are weighted by darts thrown. Checkout % = legs checked "
               "out / darts thrown at a double. Legs lost to the CPU count as not checked out.")
