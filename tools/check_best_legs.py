"""Print the fewest-dart checked-out 501 legs with their visits (read-only)."""
import sqlite3
import sys

con = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
for leg_id, darts, created in con.execute(
        "select id, gesamtDarts, created_at from xGame where startScore=501 and gesamtScore=501 "
        "order by gesamtDarts limit 3"):
    visits = con.execute("select score, darts from aufnahme where entityName='XGame' and entityId=? "
                         "order by round", (leg_id,)).fetchall()
    print(leg_id, created, darts, "darts:", visits)
