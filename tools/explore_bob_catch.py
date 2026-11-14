"""Explore Bob27 and Catch40 data shape (read-only).

Usage: python tools/explore_bob_catch.py <mdt.db>
"""
import sqlite3
import sys

con = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
q = lambda s, *p: con.execute(s, p).fetchall()

print("==== Bob27")
print("rows:", q("select count(*), min(created_at), max(created_at) from Bob27"))
print("easyMode:", q("select easyMode, count(*) from Bob27 group by 1"))
print("runden dist:", q("select runden, count(*) from Bob27 group by 1 order by 1"))
print("lastTarget dist:", q("select lastTarget, count(*) from Bob27 group by 1 order by 2 desc limit 25"))
print("punkte stats:", q("select min(punkte), avg(punkte), max(punkte), sum(punkte=0), sum(punkte<0) from Bob27"))
print("shots vs runden*3:", q("select sum(shotsOnTarget = runden*3), count(*) from Bob27"))
print("by profile:", q("select profileId, count(*) from Bob27 group by 1"))
print("sample rows (best, latest, a zero):")
for r in q("select * from Bob27 order by punkte desc limit 3"): print("   ", r)
for r in q("select * from Bob27 order by created_at desc limit 3"): print("   ", r)
for r in q("select * from Bob27 where punkte=0 limit 3"): print("   ", r)
b = q("select id from Bob27 order by punkte desc limit 1")[0][0]
print(f"dartTarget rows for best Bob27 {b}:")
for r in q("select target, shotsOnTarget, hits, open from dartTarget where entityName='Bob27' and entityId=? order by id", b):
    print("   ", r)
z = q("select id from Bob27 where punkte=0 order by created_at desc limit 1")
if z:
    print(f"dartTarget rows for zero Bob27 {z[0][0]}:")
    for r in q("select target, shotsOnTarget, hits, open from dartTarget where entityName='Bob27' and entityId=? order by id", z[0][0]):
        print("   ", r)
print("bob games without dartTarget rows:", q(
    "select count(*) from Bob27 b where not exists (select 1 from dartTarget d where d.entityName='Bob27' and d.entityId=b.id)"))
print("sum(dartTarget.hits) == Bob27.hits:", q(
    "select sum(b.hits = (select sum(hits) from dartTarget d where d.entityName='Bob27' and d.entityId=b.id)), count(*) from Bob27 b"))
print("dartTarget targets:", q("select target, count(*) from dartTarget where entityName='Bob27' group by 1 order by 1"))
print("open values:", q("select open, count(*) from dartTarget where entityName='Bob27' group by 1"))

# Reconstruct score from targets (standard Bob's 27 rules) and compare with punkte
def value(t):
    if t in ("DB", "BULL", "D25", "Bull", "DBULL"):
        return 50
    return int(t[1:]) * 2 if t.startswith("D") and t[1:].isdigit() else None

mismatch = 0
ex = []
for (gid, punkte, easy) in q("select id, punkte, easyMode from Bob27"):
    s = 27
    for (t, shots, hits) in q("select target, shotsOnTarget, hits from dartTarget where entityName='Bob27' and entityId=? order by id", gid):
        v = value(t)
        if v is None:
            break
        s += hits * v if hits else -v
    if s != punkte and (max(s, 0) != punkte):
        mismatch += 1
        if len(ex) < 5:
            ex.append((gid, punkte, s, easy))
print("reconstruction mismatches (allowing clamp at 0):", mismatch, ex)

print("\n==== Catch40")
print("rows:", q("select count(*), min(created_at), max(created_at) from Catch40"))
print("modus:", q("select modus, count(*) from Catch40 group by 1"))
print("checkouts/punkte stats:", q("select min(checkouts), avg(checkouts), max(checkouts), min(punkte), avg(punkte), max(punkte) from Catch40"))
print("by profile:", q("select profileId, count(*) from Catch40 group by 1"))
for r in q("select * from Catch40 order by created_at desc limit 3"): print("   ", r)
c = q("select id from Catch40 order by created_at desc limit 1")[0][0]
print(f"Finish rows for latest Catch40 {c}:")
for r in q("select score, minDartsToFinish, maxDartsToFinish, darts, punkte, checkout from Finish where entityName='Catch40' and entityId=? order by id", c):
    print("   ", r)
print("Finish per game count dist:", q(
    "select n, count(*) from (select entityId, count(*) n from Finish where entityName='Catch40' group by 1) group by 1"))
print("score range per modus:", q(
    "select c.modus, min(f.score), max(f.score), count(*) from Finish f join Catch40 c on c.id=f.entityId "
    "where f.entityName='Catch40' group by 1"))
print("darts vs punkte vs checkout:", q(
    "select checkout, darts, punkte, count(*) from Finish where entityName='Catch40' group by 1,2,3 order by 1,2,3"))
print("sum Finish.punkte == Catch40.punkte:", q(
    "select sum(c.punkte = (select sum(punkte) from Finish f where f.entityName='Catch40' and f.entityId=c.id)), count(*) from Catch40 c"))
print("sum Finish.checkout == Catch40.checkouts:", q(
    "select sum(c.checkouts = (select sum(checkout) from Finish f where f.entityName='Catch40' and f.entityId=c.id)), count(*) from Catch40 c"))
print("games without Finish rows:", q(
    "select count(*) from Catch40 c where not exists (select 1 from Finish f where f.entityName='Catch40' and f.entityId=c.id)"))
print("playTime cid for Bob27 ids / Catch40 ids (sample):", q(
    "select entityCid, count(*) from playTime where entityId in (select id from Bob27) group by 1 order by 2 desc limit 5"),
    q("select entityCid, count(*) from playTime where entityId in (select id from Catch40) group by 1 order by 2 desc limit 5"))
