"""Merge an Android "My Darts Training" mdt database into an iPhone one.

The Android file is used as the base (its schema is what the Android app expects).
Android row ids, and the columns that reference other Android rows, are shifted
by OFFSET. iPhone rows are then copied in unchanged. Inputs are never modified.

Usage:
    python merge_mdt.py <android mdt.db> <iphone .mdt> <output .db> [--offset 100000]
"""
import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

# Tables whose Android rows get id + OFFSET.
OFFSET_TABLES = {
    "Bob27", "Catch40", "Cricket", "Finish", "Game121", "Game420", "HalveItGame",
    "HalveItGameRound", "OneOrTen", "aufnahme", "challenge", "challengeGame",
    "cricketScoring", "cricketScoringTarget", "customScoring", "customScoringTarget",
    "dart", "dartTarget", "jdcChallenge", "jdcScoringTarget", "playTime",
    "practice_guru_100", "practice_guru_57", "priestleysTriples",
    "priestleysTriplesTarget", "randomTarget", "rtw", "rtwScoring", "rtwScoringTarget",
    "scoring", "shanghai", "shanghaiTarget", "targetFavorite", "targetTraining", "xGame",
}

# Columns in Android rows that point at other (offset) Android rows.
OFFSET_REFS = {
    "aufnahme": ["entityId"], "Finish": ["entityId"], "dartTarget": ["entityId"],
    "dart": ["entityId"], "playTime": ["entityId"],
    "HalveItGameRound": ["halveItGameId"], "rtwScoringTarget": ["rtwScoringId"],
    "challengeGame": ["xGameId", "entityId"], "cricketScoringTarget": ["cricketId"],
    "customScoringTarget": ["entityId"], "priestleysTriplesTarget": ["entityId"],
    "jdcScoringTarget": ["jdcChallengeId"], "shanghaiTarget": ["shanghaiId"],
}

# Tables handled specially (not offset).
KEEP_ANDROID = {"android_metadata", "sqlite_sequence", "HalveIt", "HalveItRound", "Profile"}

# Android tables that must be empty: player/multiplayer data needs id mapping we don't do.
MUST_BE_EMPTY = {"Spieler", "xGameMp", "xGameMpSet", "xGameMpLeg", "xGameSpieler", "aufnahmeMp"}

# Built-in definitions: keep one copy (Android's), skip the iPhone's.
DEFINITION_TABLES = {"HalveIt", "HalveItRound"}

# entityName -> table, for validating polymorphic references.
ENTITY_TABLE = {"XGame": "xGame", "JdcChallenge": "jdcChallenge"}


def tables(con, schema="main"):
    return [r[0] for r in con.execute(
        f"select name from {schema}.sqlite_master where type='table' order by name")]


def cols(con, table, schema="main"):
    return [r[1] for r in con.execute(f'pragma {schema}.table_info("{table}")')]


def count(con, table, schema="main", where=""):
    return con.execute(f'select count(*) from {schema}."{table}" {where}').fetchone()[0]


def fail(msg):
    sys.exit(f"ABORT: {msg}")


def preflight(con, offset):
    """Refuse to merge Android data we don't have rules for."""
    for t in tables(con):
        n = count(con, t)
        if n == 0:
            continue
        if t in MUST_BE_EMPTY:
            fail(f"Android table {t} has {n} rows; player/multiplayer merge not supported")
        if t not in OFFSET_TABLES and t not in KEEP_ANDROID:
            fail(f"Android table {t} has {n} rows but no merge rule")
        if t in OFFSET_TABLES:
            mx = con.execute(f'select max(id) from "{t}"').fetchone()[0]
            if mx >= offset:
                fail(f"Android {t} max id {mx} >= offset {offset}")
        if "spielerId" in cols(con, t):
            bad = count(con, t, where="where coalesce(spielerId,0) != 0")
            if bad:
                fail(f"Android {t} has {bad} rows with a player id; not supported")
    names = [r[0] for r in con.execute("select name from Profile order by id")]
    if names != ["Default"]:
        fail(f"Android profiles are {names}; expected only 'Default'")
    bad = count(con, "challengeGame", where="where generatedCpuGameInMdt != 0")
    if bad:
        fail("challengeGame rows with generatedCpuGameInMdt != 0 not supported")


def merge(android: Path, iphone: Path, out: Path, offset: int) -> None:
    if out.exists():
        fail(f"{out} already exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(android, out)
    con = sqlite3.connect(out, uri=True)
    con.execute("attach database ? as ip", (f"file:{iphone.resolve().as_posix()}?mode=ro",))
    try:
        preflight(con, offset)
        a_counts = {t: count(con, t) for t in tables(con)}
        ip_tables = set(tables(con, "ip"))
        missing = ip_tables - set(a_counts)
        if missing:
            fail(f"iPhone has tables unknown to Android schema: {sorted(missing)}")

        con.execute("begin")
        # 1. Shift Android ids and internal references.
        for t in OFFSET_TABLES:
            if t in a_counts and a_counts[t]:
                sets = ["id = id + :o"] + [f'"{c}" = "{c}" + :o' for c in OFFSET_REFS.get(t, [])
                                          if c in cols(con, t)]
                con.execute(f'update "{t}" set {", ".join(sets)}', {"o": offset})

        # 2. Copy iPhone rows.
        copied = {}
        for t in sorted(ip_tables):
            if t in ("android_metadata", "sqlite_sequence") or t in DEFINITION_TABLES:
                continue
            n = count(con, t, "ip")
            if not n:
                continue
            common = [c for c in cols(con, t, "ip") if c in cols(con, t)]
            cl = ", ".join(f'"{c}"' for c in common)
            where = "where id not in (select id from main.Profile)" if t == "Profile" else ""
            cur = con.execute(f'insert into main."{t}" ({cl}) select {cl} from ip."{t}" {where}')
            copied[t] = cur.rowcount

        # 3. Drop Android favourite targets that the iPhone already has.
        con.execute(
            "delete from targetFavorite where id >= ? and key in "
            "(select key from ip.targetFavorite)", (offset,))
        con.execute("commit")
        validate(con, offset, a_counts, copied)
        con.execute("detach database ip")
        con.execute("vacuum")
    except BaseException:
        if con.in_transaction:
            con.execute("rollback")
        con.close()
        out.unlink(missing_ok=True)  # never leave a half-merged file behind
        raise
    con.close()
    print(f"\nWrote {out}")


def validate(con, offset, a_counts, copied):
    print(f"{'table':26}{'android':>9}{'iphone':>9}{'merged':>9}")
    for t in sorted(set(a_counts) | set(copied)):
        m = count(con, t)
        a, i = a_counts.get(t, 0), copied.get(t, 0)
        if a or i:
            print(f"{t:26}{a:>9}{i:>9}{m:>9}")
        expected = a + i
        if t == "targetFavorite":
            expected = m  # duplicates removed on purpose
        if m != expected:
            fail(f"{t}: merged {m} != android {a} + iphone {i}")

    # Every shifted Android reference must resolve to an Android row.
    def check(table, col, target, where=""):
        bad = con.execute(
            f'select count(*) from "{table}" where id >= :o {where} and "{col}" not in '
            f'(select id from "{target}" where id >= :o)', {"o": offset}).fetchone()[0]
        if bad:
            fail(f"{bad} Android rows in {table}.{col} don't resolve to {target}")

    for t in ("aufnahme", "Finish", "dartTarget"):
        for (name,) in con.execute(
                f'select distinct entityName from "{t}" where id >= ?', (offset,)):
            check(t, "entityId", ENTITY_TABLE.get(name, name), f"and entityName = '{name}'")
    check("dart", "entityId", "aufnahme", "and entityCid = 100")
    check("HalveItGameRound", "halveItGameId", "HalveItGame")
    check("rtwScoringTarget", "rtwScoringId", "rtwScoring")
    check("challengeGame", "xGameId", "xGame")
    check("challengeGame", "entityId", "challenge")
    unshifted = con.execute(
        "select count(*) from playTime where id >= ? and entityId < ?", (offset, offset)
    ).fetchone()[0]
    if unshifted:
        fail(f"{unshifted} Android playTime rows not shifted")

    if con.execute("pragma integrity_check").fetchone()[0] != "ok":
        fail("integrity check failed")
    print("\nValidation passed: counts match, Android references resolve, integrity ok, "
          f"user_version {con.execute('pragma user_version').fetchone()[0]}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("android", type=Path)
    p.add_argument("iphone", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--offset", type=int, default=100000)
    a = p.parse_args()
    merge(a.android, a.iphone, a.output, a.offset)
