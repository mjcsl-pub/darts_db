"""Export the "My Darts Training" databases from a connected Fire tablet.

Flow: adb backup (tablet shows a confirm prompt) -> unpack .ab -> merge WAL
files into plain SQLite files -> save to exports/<timestamp>/ and exports/latest/.

Usage:
    python sync_darts.py            # one export now (waits for the device)
    python sync_darts.py --watch    # keep running, export each time the tablet is plugged in
"""
import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from ab_extract import extract

PACKAGE = "at.steirersoft.mydarttraining"
DB_NAMES = ["mdt", "cpuOpponent"]
if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent  # folder containing the .exe
else:
    ROOT = Path(__file__).resolve().parent
EXPORTS = ROOT / "exports"
ADB_FALLBACK = (
    Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    / "Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe/platform-tools/adb.exe"
)
BACKUP_TIMEOUT = 300  # seconds to wait for the on-tablet confirmation + transfer


def find_adb() -> str:
    found = shutil.which("adb")
    if found:
        return found
    if ADB_FALLBACK.exists():
        return str(ADB_FALLBACK)
    sys.exit("adb not found. Install with: winget install Google.PlatformTools")


def device_state(adb: str) -> str:
    out = subprocess.run([adb, "get-state"], capture_output=True, text=True).stdout.strip()
    return out or "none"


def merge_wal(src_dir: Path, name: str, dest: Path) -> None:
    """Copy db + -wal/-shm to a temp dir, checkpoint, and write a single file."""
    with tempfile.TemporaryDirectory() as tmp:
        for suffix in ("", "-wal", "-shm"):
            f = src_dir / (name + suffix)
            if f.exists():
                shutil.copy(f, Path(tmp) / (name + suffix))
        con = sqlite3.connect(Path(tmp) / name)
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError(f"integrity check failed for {name}")
        con.execute("PRAGMA journal_mode=DELETE")
        con.close()
        shutil.copy(Path(tmp) / name, dest)


def export_once(adb: str) -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = EXPORTS / stamp
    with tempfile.TemporaryDirectory() as tmp:
        ab = Path(tmp) / "backup.ab"
        print(">> Starting backup. On the tablet tap 'Back up my data' (leave password empty).")
        subprocess.run(
            [adb, "backup", "-f", str(ab), PACKAGE], check=True, timeout=BACKUP_TIMEOUT
        )
        if not ab.exists() or ab.stat().st_size < 1000:
            raise RuntimeError("backup is empty; the prompt was probably not accepted")
        files = extract(ab, Path(tmp) / "x")
        db_dir = next((f.parent for f in files if f.parent.name == "db"), None)
        if db_dir is None:
            raise RuntimeError("no db folder found in backup")
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in DB_NAMES:
            merge_wal(db_dir, name, out_dir / f"{name}.db")
    print(f">> Saved {out_dir}")
    update_latest(out_dir)
    return out_dir


def update_latest(out_dir: Path) -> None:
    """Copy the new export into exports/latest, one file at a time.

    A file that is open in another program (e.g. a SQLite viewer) can't be
    replaced on Windows; report that instead of silently leaving old data.
    """
    latest = EXPORTS / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    locked = []
    for src in out_dir.iterdir():
        tmp = latest / (src.name + ".new")
        shutil.copy2(src, tmp)
        try:
            os.replace(tmp, latest / src.name)
        except PermissionError:
            tmp.unlink(missing_ok=True)
            locked.append(src.name)
    if locked:
        print(f"!! exports/latest NOT fully updated: {', '.join(locked)} is open in another "
              f"program. Close it and run again, or use {out_dir}")
    else:
        print(f">> Updated {latest}")


def wait_for_device(adb: str) -> None:
    while device_state(adb) != "device":
        time.sleep(3)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--watch", action="store_true", help="export on every (re)connect")
    args = p.parse_args()
    adb = find_adb()

    if not args.watch:
        try:
            print(">> Waiting for the tablet (USB debugging on, unlocked)...")
            wait_for_device(adb)
            export_once(adb)
            print(">> Done.")
        except Exception as e:
            print(f"!! Export failed: {e}")
        input("Press Enter to close...")
        return

    print(">> Watching for the tablet. Ctrl+C to stop.")
    was_connected = False
    while True:
        connected = device_state(adb) == "device"
        if connected and not was_connected:
            try:
                export_once(adb)
            except Exception as e:  # keep watching after a failed attempt
                print(f"!! Export failed: {e}")
        was_connected = connected
        time.sleep(5)


if __name__ == "__main__":
    main()
