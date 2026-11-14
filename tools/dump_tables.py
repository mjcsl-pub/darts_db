"""Print columns and sample rows of every non-empty table (read-only).

Usage: python tools/dump_tables.py <db> [rows_per_table]
"""
import sqlite3
import sys

db = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
for (t, sql) in con.execute(
    "select name, sql from sqlite_master where type='table' order by name"
).fetchall():
    n = con.execute(f'select count(*) from "{t}"').fetchone()[0]
    if n == 0:
        continue
    print(f"== {t} ({n} rows)")
    print(f"   {sql}")
    for r in con.execute(f'select * from "{t}" limit {limit}'):
        print("   ", r)
con.close()
