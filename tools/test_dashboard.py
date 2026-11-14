"""Headless smoke test of the dashboard: runs every Group-by option and reports errors.

Usage: python tools/test_dashboard.py
"""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

app = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
sys.path.insert(0, str(app.parent))

failed = False
for period in ["Month", "Leg", "Week", "Quarter", "Year"]:
    at = AppTest.from_file(str(app), default_timeout=120).run()
    if at.exception:
        print("initial run exception:", [e.message for e in at.exception]); failed = True; break
    sb = [s for s in at.sidebar.selectbox if s.label == "Group by"][0]
    sb.set_value(period).run()
    errs = [e.message for e in at.exception] + [e.value for e in at.error]
    db = [s for s in at.sidebar.selectbox if s.label == "Database"][0].value
    metrics = {m.label: m.value for m in at.metric}
    print(f"{period:8} db={db} errors={errs or 'none'}")
    if period == "Month":
        print("   metrics:", metrics)
    failed |= bool(errs)
print("FAILED" if failed else "OK")
