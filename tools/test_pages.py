"""Headless test of the Bob's 27 and Catch 40 pages plus data checks.

Usage: python tools/test_pages.py
"""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

DASH = Path(__file__).resolve().parent.parent / "dashboard"
sys.path.insert(0, str(DASH))

failed = False

# 1. Data checks against the app's own stored values
import data  # noqa: E402

db = data.find_databases()[0]
games, targets = data.load_bob27(str(db), db.stat().st_mtime)
last = targets.groupby("game_id")["score_after"].last()
bad = (games.set_index("game_id")["score"] != last.reindex(games["game_id"]).values).sum()
print(f"db {db.name} ({db.parent.name})")
print(f"Bob27: {len(games)} games, rebuilt final score mismatches: {bad}")
failed |= bool(bad)

cg, ct = data.load_catch40(str(db), db.stat().st_mtime)
bad = (cg["points"] != cg["points_calc"]).sum()
print(f"Catch40: {len(cg)} games, points mismatches: {bad}, modes {cg['mode_name'].value_counts().to_dict()}")
failed |= bool(bad)

# 2. Render each page with every grouping option
for mod, key in (("bob27", "bob_period"), ("catch40", "catch_period")):
    script = (f"import sys\nsys.path.insert(0, r'{DASH}')\nimport streamlit as st\n"
              f"st.set_page_config(layout='wide')\nimport {mod}\n{mod}.render()\n")
    for period in ["Game", "Week", "Month", "Quarter", "Year"]:
        at = AppTest.from_string(script, default_timeout=120).run()
        if not at.exception:
            sel = [s for s in at.sidebar.selectbox if s.key == key]
            if sel:
                sel[0].set_value(period).run()
        errs = [e.message for e in at.exception] + [e.value for e in at.error]
        metrics = {m.label: m.value for m in at.metric}
        print(f"{mod:8} {period:8} errors={errs or 'none'}")
        if period == "Game":
            print("   metrics:", metrics)
        failed |= bool(errs)
    if mod == "catch40":
        at = AppTest.from_string(script, default_timeout=120).run()
        radio = [r for r in at.sidebar.radio if r.key == "catch_mode"][0]
        for opt in radio.options:
            radio.set_value(opt).run()
            errs = [e.message for e in at.exception] + [e.value for e in at.error]
            print(f"catch40  mode {opt}: errors={errs or 'none'} games={[m.value for m in at.metric][:1]}")
            failed |= bool(errs)

print("FAILED" if failed else "OK")
