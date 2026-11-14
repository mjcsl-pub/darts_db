"""Search printable strings in a binary (e.g. classes.dex) for keywords.

Usage: python tools/dex_strings.py <file> word1 [word2 ...]
"""
import re
import sys

data = open(sys.argv[1], "rb").read()
words = [w.lower() for w in sys.argv[2:]]
seen = set()
for m in re.finditer(rb"[\x20-\x7e]{4,200}", data):
    s = m.group().decode()
    ls = s.lower()
    if any(w in ls for w in words) and s not in seen:
        seen.add(s)
for s in sorted(seen)[:300]:
    print(s)
print(f"-- {len(seen)} matches")
