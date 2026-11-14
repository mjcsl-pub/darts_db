"""Print max(id) per table and columns that look like references (…Id / …_id).

Usage: python tools/max_ids.py file1 [file2 ...]   (opened read-only)
"""
import sqlite3
import sys

for path in sys.argv[1:]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    print(f"== {path}")
    tables = [r[0] for r in con.execute(
        "select name from sqlite_master where type='table' order by name")]
    for t in tables:
        cols = [r[1] for r in con.execute(f'pragma table_info("{t}")')]
        n = con.execute(f'select count(*) from "{t}"').fetchone()[0]
        if n == 0:
            continue
        idcol = next((c for c in cols if c.lower() in ("id", "_id")), None)
        mx = con.execute(f'select max("{idcol}") from "{t}"').fetchone()[0] if idcol else "-"
        refs = [c for c in cols if c != idcol and (c.lower().endswith("id") or c.lower().endswith("_id"))]
        fks = [f"{r[3]}->{r[2]}" for r in con.execute(f'pragma foreign_key_list("{t}")')]
        print(f"  {t:28} rows {n:>7}  max {idcol}={mx!s:>8}  refs {refs} fks {fks}")
    con.close()
