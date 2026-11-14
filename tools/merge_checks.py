"""Pre-merge checks between the Android and iPhone databases (read-only).

Usage: python tools/merge_checks.py <android.db> <iphone.mdt>
"""
import sqlite3
import sys

a = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
i = sqlite3.connect(f"file:{sys.argv[2]}?mode=ro", uri=True)

def both(sql):
    return a.execute(sql).fetchall(), i.execute(sql).fetchall()

for t, c in [("aufnahme", "entityName"), ("Finish", "entityName"), ("dartTarget", "entityName"),
             ("challengeGame", "entityName"), ("dart", "entityCid"), ("playTime", "entityCid"),
             ("challengeGame", "generatedCpuGameInMdt"), ("challenge", "cpuOpponentId"),
             ("challenge", "challengeModus")]:
    ra, ri = both(f'select "{c}", count(*) from "{t}" group by 1 order by 1')
    print(f"{t}.{c}\n   android {ra}\n   iphone  {ri}")

for t in ("HalveIt", "HalveItRound"):
    cols = [r[1] for r in a.execute(f"pragma table_info({t})") if r[1] != "created_at"]
    sel = f"select {','.join(cols)} from {t} order by id"
    ra, ri = both(sel)
    print(f"{t} identical (ignoring created_at): {ra == ri}")

# Where does dart.entityId (cid 100/101) point? Compare with aufnahme ids per cid.
for cid in (100, 101):
    for name, con in (("android", a), ("iphone", i)):
        r = con.execute(
            "select count(*), sum(entityId in (select id from aufnahme)), "
            "sum(entityId in (select id from aufnahmeMp)) from dart where entityCid=?", (cid,)
        ).fetchone()
        print(f"dart cid {cid} {name}: rows {r[0]}, in aufnahme {r[1]}, in aufnahmeMp {r[2]}")

# playTime: entityCid -> which table? check against each candidate table for android
cands = ["Bob27", "Catch40", "Game121", "HalveItGame", "xGame", "challenge", "scoring", "rtw",
         "rtwScoring", "targetTraining", "practice_guru_57", "randomTarget", "Finish"]
for (cid,) in a.execute("select distinct entityCid from playTime order by 1"):
    ids = [r[0] for r in a.execute("select entityId from playTime where entityCid=?", (cid,))]
    fits = [t for t in cands if all(
        a.execute(f"select 1 from {t} where id=?", (x,)).fetchone() for x in ids)]
    print(f"playTime cid {cid}: entityIds {sorted(set(ids))[:10]} fits {fits}")

print("android sqlite_sequence:", a.execute("select * from sqlite_sequence").fetchall())
print("android indexes/triggers/views:", a.execute(
    "select type, name, tbl_name from sqlite_master where type in ('index','trigger','view')").fetchall())
print("iphone  indexes/triggers/views:", i.execute(
    "select type, name, tbl_name from sqlite_master where type in ('index','trigger','view')").fetchall())
print("user_version android/iphone:", a.execute("pragma user_version").fetchone(),
      i.execute("pragma user_version").fetchone())
print("iphone latest created_at per main table:")
for t in ("xGame", "aufnahme", "dart", "playTime", "challenge"):
    print("  ", t, i.execute(f"select min(created_at), max(created_at) from {t}").fetchone())
print("android earliest created_at xGame:", a.execute("select min(created_at) from xGame").fetchone())
