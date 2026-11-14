"""Show rows in db A that are missing from db B (by id), for given tables (read-only).

Usage: python tools/diff_rows.py <a.db> <b.db> table1 [table2 ...]
"""
import sqlite3
import sys

a, b = sys.argv[1], sys.argv[2]
con = sqlite3.connect(f"file:{a}?mode=ro", uri=True)
con.execute("attach database ? as b", (f"file:{b}?mode=ro",))
for t in sys.argv[3:]:
    rows = con.execute(f'select * from main."{t}" where id not in (select id from b."{t}")').fetchall()
    print(f"== {t}: {len(rows)} rows only in A")
    for r in rows[:10]:
        print("   ", r)
