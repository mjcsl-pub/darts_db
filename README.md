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

## Files

| File | Purpose |
|------|---------|
| `sync_darts.py` | Main script: backup, unpack, save |
| `ab_extract.py` | Unpacks unencrypted Android `.ab` backups |
| `tools/inspect_db.py` | Prints integrity and row counts of exported DBs |

## Notes

- `adb backup` is deprecated but still works on Fire OS 9 (Android 9).
- Encrypted backups are not supported.
