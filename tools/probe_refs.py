"""Investigate what reference columns point to (read-only).

Usage: python tools/probe_refs.py <db>
"""
import sqlite3
import sys

db = sys.argv[1]
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
q = lambda s: con.execute(s).fetchall()

print("== Profile");      [print("  ", r) for r in q("select * from Profile")]
print("== Spieler cols", [r[1] for r in q("pragma table_info(Spieler)")])
print("== HalveIt");      [print("  ", r) for r in q("select * from HalveIt")]
print("== HalveItRound (first 3)"); [print("  ", r) for r in q("select * from HalveItRound limit 3")]
print("== targetFavorite"); [print("  ", r) for r in q("select * from targetFavorite")]

def dist(table, col, extra=""):
    rows = q(f'select "{col}", count(*) from "{table}" {extra} group by 1 order by 2 desc limit 12')
    print(f"== {table}.{col} values:", rows)

for t in ("dart", "playTime"):
    dist(t, "entityCid")

# For entityId columns: min/max and how many match ids in candidate parent tables
tables = [r[0] for r in q("select name from sqlite_master where type='table'")]
cand = [t for t in tables if "id" in [c[1].lower() for c in q(f'pragma table_info("{t}")')]]
def ref_check(table, col, where=""):
    vals = q(f'select distinct "{col}" from "{table}" {where}')
    vals = {v[0] for v in vals}
    if not vals:
        return
    hits = []
    for c in cand:
        ids = {r[0] for r in q(f'select id from "{c}"')}
        if not ids:
            continue
        m = len(vals & ids)
        if m == len(vals - {None, 0, -1}) and m:
            hits.append(c)
    print(f"   {table}.{col} {where}: {len(vals)} distinct, min {min(v for v in vals if v is not None) if vals - {None} else None}, "
          f"max {max(v for v in vals if v is not None) if vals - {None} else None}, "
          f"null/0/-1 {sorted(str(v) for v in vals & {None, 0, -1})}, fully contained in: {hits[:8]}")

print("== reference containment")
for t in tables:
    cols = [c[1] for c in q(f'pragma table_info("{t}")')]
    for c in cols:
        lc = c.lower()
        if lc != "id" and (lc.endswith("id") or lc.endswith("_id")) and lc != "entitycid":
            if t in ("dart", "playTime") and lc == "entityid":
                for (cid,) in q(f'select distinct entityCid from "{t}"'):
                    ref_check(t, c, f"where entityCid = {cid!r}" if cid is not None else "where entityCid is null")
            else:
                ref_check(t, c)
con.close()
