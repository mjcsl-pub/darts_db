"""Search strings in all .dex files and resources.arsc inside an APK.

Usage: python tools/apk_strings.py <app.apk> word1 [word2 ...]
"""
import re
import sys
import zipfile

words = [w.lower() for w in sys.argv[2:]]
found = set()
with zipfile.ZipFile(sys.argv[1]) as z:
    for name in z.namelist():
        if not (name.endswith(".dex") or name == "resources.arsc"):
            continue
        data = z.read(name)
        texts = [m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{4,200}", data)]
        if name == "resources.arsc":  # also UTF-16LE strings
            texts += [m.group().decode("utf-16le") for m in
                      re.finditer(rb"(?:[\x20-\x7e]\x00){4,200}", data)]
        for s in texts:
            if any(w in s.lower() for w in words):
                found.add(s)
for s in sorted(found)[:400]:
    print(s)
print(f"-- {len(found)} matches")
