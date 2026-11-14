"""Data access for the darts dashboard.

Databases are opened read-only and closed straight after loading, so the
dashboard never locks an export (which would stop sync_darts.py updating it).
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DB_PATTERNS = ["exports/*/mdt.db", "dist/exports/*/mdt.db", "exports/merged/*.db"]


def find_databases() -> list[Path]:
    """All exported mdt databases, newest first."""
    found = {p.resolve() for pat in DB_PATTERNS for p in ROOT.glob(pat)}
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def source_picker() -> Path:
    dbs = find_databases()
    if not dbs:
        st.error("No exported database found. Run DartsBackup.exe or sync_darts.py first.")
        st.stop()
    labels = {str(p.relative_to(ROOT)): p for p in dbs}
    choice = st.sidebar.selectbox("Database", list(labels), help="Newest export first")
    return labels[choice]


def _read(path: Path, sql: str, params: tuple = ()) -> pd.DataFrame:
    with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as con:
        return pd.read_sql_query(sql, con, params=params)


LEGS_SQL = """
select x.id as leg_id, x.created_at, x.profileId as profile_id,
       coalesce(p.name, 'Profile ' || x.profileId) as profile,
       x.gesamtScore as scored, x.gesamtDarts as darts,
       cg.win, cg.setNummer as set_no, cg.legNummer as leg_no,
       c.id as challenge_id, c.cpuLevel as cpu_level
from xGame x
left join Profile p on p.id = x.profileId
left join (select xGameId, max(win) as win, min(setNummer) as setNummer,
                  min(legNummer) as legNummer, min(entityId) as entityId
           from challengeGame group by xGameId) cg on cg.xGameId = x.id
left join challenge c on c.id = cg.entityId
where x.startScore = ?
"""

VISITS_SQL = """
select a.entityId as leg_id, a.round, a.beginnScore as remaining, a.score, a.darts,
       a.dartsOnDouble as darts_at_double, a.checkout
from aufnahme a join xGame x on x.id = a.entityId
where a.entityName = 'XGame' and x.startScore = ?
order by a.entityId, a.round
"""


DARTS_SQL = """
select d.id as dart_id, d.nummer as dart_no, d.startScore as remaining, d.target, d.targetValue as value,
       a.id as visit_id, a.entityId as leg_id, a.round, a.score as visit_score, a.checkout as visit_checkout
from dart d
join aufnahme a on a.id = d.entityId and a.entityName = 'XGame'
join xGame x on x.id = a.entityId
where d.entityCid = 100 and x.startScore = ?
order by d.id
"""


@st.cache_data(show_spinner="Loading darts...")
def load_x01_darts(path_str: str, mtime: float, start_score: int) -> pd.DataFrame:
    """One row per recorded dart of X01 legs (dart.entityId points to aufnahme.id).

    `is_checkout` marks the last dart of a visit that checked out.
    """
    darts = _read(Path(path_str), DARTS_SQL, (start_score,))
    if darts.empty:
        return darts
    last = darts.groupby("visit_id")["dart_no"].transform("max")
    darts["is_checkout"] = (darts["visit_checkout"] == 1) & (darts["dart_no"] == last)
    return darts


BOB_SQL = """
select b.id as game_id, b.created_at, coalesce(p.name, 'Profile ' || b.profileId) as profile,
       b.punkte as score, b.hits, b.shotsOnTarget as darts, b.runden as rounds,
       b.easyMode as easy_mode, b.lastTarget as last_target
from Bob27 b left join Profile p on p.id = b.profileId
"""

BOB_TARGETS_SQL = """
select entityId as game_id, id as row_id, target, shotsOnTarget as darts, hits
from dartTarget where entityName = 'Bob27' order by entityId, id
"""

BOB_DOUBLES = [f"D{i}" for i in range(1, 21)] + ["BULL"]
BOB_VALUE = {**{f"D{i}": 2 * i for i in range(1, 21)}, "BULL": 50}


@st.cache_data(show_spinner="Loading Bob's 27...")
def load_bob27(path_str: str, mtime: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (games, targets). targets has the running score after each double."""
    path = Path(path_str)
    games = _read(path, BOB_SQL)
    targets = _read(path, BOB_TARGETS_SQL)
    if games.empty:
        return games, targets
    games["created_at"] = pd.to_datetime(games["created_at"])
    games["completed"] = games["score"] > 0
    games["hit_pct"] = games["hits"] / games["darts"].where(games["darts"] > 0) * 100

    # Bob's 27: +value per hit, -value if all three darts miss; game over at 0.
    targets["value"] = targets["target"].map(BOB_VALUE)
    targets["change"] = (targets["hits"] * targets["value"]).where(targets["hits"] > 0, -targets["value"])
    targets["score_after"] = (27 + targets.groupby("game_id")["change"].cumsum()).clip(lower=0)
    targets["double_no"] = targets["target"].map({t: i + 1 for i, t in enumerate(BOB_DOUBLES)})
    targets = targets.merge(games[["game_id", "created_at", "profile"]], on="game_id")
    return games, targets


CATCH_SQL = """
select c.id as game_id, c.created_at, coalesce(p.name, 'Profile ' || c.profileId) as profile,
       c.punkte as points, c.checkouts, c.modus as mode
from Catch40 c left join Profile p on p.id = c.profileId
"""

CATCH_FINISH_SQL = """
select entityId as game_id, id as row_id, score as target, darts, checkout
from Finish where entityName = 'Catch40' order by entityId, id
"""

CATCH_MODES = {1: "61-100", 2: "41-80"}
CATCH_POINTS = {2: 3, 3: 2, 4: 1, 5: 1, 6: 1}


@st.cache_data(show_spinner="Loading Catch 40...")
def load_catch40(path_str: str, mtime: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (games, targets). Points per target follow the app: 2 darts=3, 3=2, 4-6=1."""
    path = Path(path_str)
    games = _read(path, CATCH_SQL)
    targets = _read(path, CATCH_FINISH_SQL)
    if games.empty:
        return games, targets
    games["created_at"] = pd.to_datetime(games["created_at"])
    games["mode_name"] = games["mode"].map(CATCH_MODES).fillna("mode " + games["mode"].astype(str))

    targets["points"] = targets["darts"].map(CATCH_POINTS).where(targets["checkout"] == 1, 0).fillna(0)
    co = targets[targets["checkout"] == 1]
    per = pd.DataFrame({
        "targets": targets.groupby("game_id").size(),
        "points_calc": targets.groupby("game_id")["points"].sum(),
        "co2": co[co["darts"] == 2].groupby("game_id").size(),
        "co3": co[co["darts"] == 3].groupby("game_id").size(),
        "co4_6": co[co["darts"] >= 4].groupby("game_id").size(),
        "co_darts": co.groupby("game_id")["darts"].sum(),
    }).fillna(0)
    games = games.merge(per, left_on="game_id", right_index=True, how="left")
    games["checkout_pct"] = games["checkouts"] / games["targets"].where(games["targets"] > 0) * 100
    targets = targets.merge(games[["game_id", "created_at", "profile", "mode_name"]], on="game_id")
    return games, targets


@st.cache_data(show_spinner="Loading games...")
def load_x01(path_str: str, mtime: float, start_score: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (legs, visits) for X01 legs with the given start score.

    `mtime` is only part of the cache key, so a newer export is re-read.
    """
    path = Path(path_str)
    legs = _read(path, LEGS_SQL, (start_score,))
    visits = _read(path, VISITS_SQL, (start_score,))
    if legs.empty:
        return legs, visits

    legs["created_at"] = pd.to_datetime(legs["created_at"])
    legs["mode"] = legs["challenge_id"].notna().map({True: "vs CPU", False: "Training"})
    legs["checked_out"] = legs["scored"] == start_score

    g = visits.groupby("leg_id")
    per_leg = pd.DataFrame({
        "visits": g.size(),
        "highest_visit": g["score"].max(),
        "n100": g["score"].apply(lambda s: ((s >= 100) & (s < 140)).sum()),
        "n140": g["score"].apply(lambda s: ((s >= 140) & (s < 180)).sum()),
        "n180": g["score"].apply(lambda s: (s == 180).sum()),
        "darts_at_double": g["darts_at_double"].sum(),
    })
    f9 = visits[visits["round"] <= 3].groupby("leg_id")[["score", "darts"]].sum()
    per_leg["f9_score"], per_leg["f9_darts"] = f9["score"], f9["darts"]
    co = visits[visits["checkout"] == 1].groupby("leg_id")["remaining"].max()
    per_leg["checkout_value"] = co

    legs = legs.merge(per_leg, left_on="leg_id", right_index=True, how="left")
    legs["avg3"] = legs["scored"] / legs["darts"].where(legs["darts"] > 0) * 3
    legs["first9"] = legs["f9_score"] / legs["f9_darts"].where(legs["f9_darts"] > 0) * 3
    legs = legs.sort_values(["created_at", "leg_id"]).reset_index(drop=True)
    return legs, visits
