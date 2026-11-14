"""Explore X01 data shape (read-only). Usage: python tools/explore_x01.py <mdt.db>"""
import sqlite3
import sys

con = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
q = lambda s, *p: con.execute(s, p).fetchall()

print("startScore counts:", q("select startScore, count(*) from xGame group by 1 order by 2 desc"))
print("501 by checkoutModus/doubleIn/dartsOnDouble:",
      q("select checkoutModus, doubleIn, dartsOnDouble, count(*) from xGame where startScore=501 group by 1,2,3"))
print("501 finished (gesamtScore=startScore):",
      q("select gesamtScore = startScore, count(*) from xGame where startScore=501 group by 1"))
print("501 by profile:", q("select profileId, count(*) from xGame where startScore=501 group by 1"))
print("501 by year:", q("select substr(created_at,1,4), count(*) from xGame where startScore=501 group by 1"))
print("501 in challenge (CPU) legs:",
      q("select count(*) from xGame x where startScore=501 and id in (select xGameId from challengeGame)"))
print("same created_at groups (legs per session?):",
      q("select n, count(*) from (select created_at, count(*) n from xGame where startScore=501 group by 1) group by 1 order by 1"))

g = q("select id from xGame where startScore=501 and gesamtScore=501 order by created_at desc limit 1")[0][0]
print("\nsample finished 501 game:", q("select * from xGame where id=?", g))
for r in q("select * from aufnahme where entityName='XGame' and entityId=? order by round", g):
    print("   ", r)
u = q("select id from xGame where startScore=501 and gesamtScore<501 order by created_at desc limit 1")
if u:
    print("sample unfinished 501 game:", q("select * from xGame where id=?", u[0][0]))
    for r in q("select * from aufnahme where entityName='XGame' and entityId=? order by round", u[0][0]):
        print("   ", r)
print("\naufnahme.checkout values (501):", q(
    "select a.checkout, count(*) from aufnahme a join xGame x on x.id=a.entityId and a.entityName='XGame' "
    "where x.startScore=501 group by 1"))
print("aufnahme.darts values (501):", q(
    "select a.darts, count(*) from aufnahme a join xGame x on x.id=a.entityId and a.entityName='XGame' "
    "where x.startScore=501 group by 1"))
print("games where sum(aufnahme.score) != gesamtScore:", q(
    "select count(*) from xGame x where startScore=501 and gesamtScore != "
    "(select coalesce(sum(score),0) from aufnahme a where a.entityName='XGame' and a.entityId=x.id)"))
print("games where sum(aufnahme.darts) != gesamtDarts:", q(
    "select count(*) from xGame x where startScore=501 and gesamtDarts != "
    "(select coalesce(sum(darts),0) from aufnahme a where a.entityName='XGame' and a.entityId=x.id)"))
print("games with no aufnahme rows:", q(
    "select count(*) from xGame x where startScore=501 and not exists "
    "(select 1 from aufnahme a where a.entityName='XGame' and a.entityId=x.id)"))
print("gesamtDarts range finished:", q(
    "select min(gesamtDarts), avg(gesamtDarts), max(gesamtDarts) from xGame where startScore=501 and gesamtScore=501"))
print("Profile:", q("select id, name from Profile"))
