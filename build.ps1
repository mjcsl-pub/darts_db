# Builds dist\DartsBackup.exe (requires: pip install -r requirements-dev.txt)
python -m PyInstaller --onefile --noconfirm --name DartsBackup sync_darts.py
