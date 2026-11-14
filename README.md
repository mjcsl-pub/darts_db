# Fire tablet "My Darts Training" backup

Exports the SQLite databases of the Android app *My Darts Training*
(`at.steirersoft.mydarttraining`) from an Amazon Fire tablet to a Windows PC over USB.

The app's data directory is not readable via `adb pull` or `run-as`, so the tool uses
`adb backup`, unpacks the `.ab` archive, merges the WAL files and saves plain `.db` files.

## Requirements

- Windows, Python 3.10+ (standard library only)
- [Android platform-tools](https://developer.android.com/tools/releases/platform-tools)
  (`winget install Google.PlatformTools`)
- Tablet: Developer Options on, **USB debugging** on, authorised for this PC

## Usage

```powershell
python sync_darts.py           # one export
python sync_darts.py --watch   # export each time the tablet is plugged in
```

Each export needs one tap on the tablet: **Back up my data** (leave the password empty).
Android requires this prompt for every `adb backup`.

Output goes to `exports/<timestamp>/` and `exports/latest/`:

- `mdt.db`: games, turns, darts, challenges
- `cpuOpponent.db`: computer-opponent game data

`exports/` is git-ignored because it holds personal data.

## Build the exe

```powershell
pip install -r requirements-dev.txt
./build.ps1
```

This produces `dist/DartsBackup.exe`. When run as an exe, `exports/` is created next to it.

## Dashboard

```powershell
pip install -r requirements.txt
python -m streamlit run dashboard/app.py    # or double-click Dashboard.bat
```

Opens in the browser at http://localhost:8501. It reads the newest export
(`exports/*/mdt.db`, `dist/exports/*/mdt.db`, `exports/merged/*.db`); pick another
in the sidebar. Databases are opened read-only and closed after loading.

**501 page** (each `xGame` row is one leg, each `aufnahme` row one 3-dart visit):

- Filters: date range, profile, mode (Training / vs CPU), group by leg, week, month,
  quarter or year; rolling window when grouped by leg
- 3-dart and first-9 averages (weighted by darts), checkout %
  (checkouts / darts at double), darts per checked-out leg, 100+/140+/180 counts,
  legs played, legs won vs CPU, checkout score histogram
- Leg table and per-leg visit breakdown

**Bob's 27 page** (`Bob27` games, per-double rows in `dartTarget`): doubles reached,
double hit %, completed games and scores over time, hit % per double and a
double-by-period heatmap, running score per game.

**Catch 40 page** (`Catch40` games, per-target rows in `Finish`): points and checkouts
per game, checkouts by darts used (2 = 3 pts, 3 = 2 pts, 4-6 = 1 pt), checkout % per
target. Target ranges 61-100 and 41-80 are shown separately.

## Merging another device's data

`merge_mdt.py` merges an Android `mdt.db` into another device's `.mdt` backup
(Android ids shifted by 100000) and validates the result. The merged file can be
imported in the app via *Backup/Restore database* from the tablet's Download folder.

## Files

| File | Purpose |
|------|---------|
| `sync_darts.py` | Main script: backup, unpack, save |
| `ab_extract.py` | Unpacks unencrypted Android `.ab` backups |
| `merge_mdt.py` | Merges two app databases with id offset and validation |
| `dashboard/` | Streamlit dashboard (`app.py`, `x01.py`, `data.py`) |
| `tools/` | Inspection and test helpers (`inspect_db.py`, `compare_db.py`, `test_dashboard.py`, ...) |

## Notes

- `adb backup` is deprecated but still works on Fire OS 9 (Android 9).
- Encrypted backups are not supported.
