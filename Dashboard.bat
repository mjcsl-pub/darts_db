@echo off
rem Starts the darts dashboard and opens it in the browser. Close this window to stop it.
cd /d "%~dp0"
python -m streamlit run dashboard\app.py
pause
