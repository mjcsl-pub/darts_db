"""Compare tables, row counts and columns of two or more SQLite files.

Usage: python tools/compare_db.py file1 file2 [file3 ...]
Files are opened read-only.
"""
import sqlite3
import sys
from pathlib import Path


def describe(path: Path) -> dict[str, tuple[int, list[str]]]:
    with open(path, "rb") as f:
        if f.read(16) != b"SQLite format 3\x00":
            raise ValueError(f"{path.name} is not a SQLite database")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    out = {}
    for (t,) in con.execute(
        "select name from sqlite_master where type='table' order by name"
    ):
        cols = [r[1] for r in con.execute(f'pragma table_info("{t}")')]
        n = con.execute(f'select count(*) from "{t}"').fetchone()[0]
        out[t] = (n, cols)
    print(f"{path.name}: integrity {con.execute('pragma integrity_check').fetchone()[0]}, "
          f"user_version {con.execute('pragma user_version').fetchone()[0]}")
    con.close()
    return out


def main() -> None:
    paths = [Path(p) for p in sys.argv[1:]]
    infos = [describe(p) for p in paths]
    tables = sorted(set().union(*infos))
    names = [p.name for p in paths]
    print()
    print(f"{'table':32}" + "".join(f"{n[:22]:>24}" for n in names))
    for t in tables:
        row = "".join(
            f"{(str(i[t][0]) if t in i else '-'):>24}" for i in infos
        )
        print(f"{t:32}{row}")
    print("\nColumn differences:")
    diffs = 0
    for t in tables:
        colsets = [set(i[t][1]) for i in infos if t in i]
        if len(colsets) > 1 and any(c != colsets[0] for c in colsets):
            diffs += 1
            for p, i in zip(names, infos):
                if t in i:
                    extra = set(i[t][1]) - set.intersection(*colsets)
                    if extra:
                        print(f"  {t}: only in {p}: {sorted(extra)}")
    if not diffs:
        print("  none (shared tables have identical columns)")


if __name__ == "__main__":
    main()
