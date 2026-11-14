"""Print integrity and table row counts for SQLite DBs (handles -wal/-shm)."""
import os
import shutil
import sqlite3
import sys
import tempfile

d = sys.argv[1]
for n in sys.argv[2:]:
    t = tempfile.mkdtemp()
    for s in ("", "-wal", "-shm"):
        src = os.path.join(d, n + s)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(t, n + s))
    c = sqlite3.connect(os.path.join(t, n))
    print(n, c.execute("pragma integrity_check").fetchone())
    for (tb,) in c.execute("select name from sqlite_master where type='table'").fetchall():
        print("  ", tb, c.execute(f'select count(*) from "{tb}"').fetchone()[0])
    c.close()
