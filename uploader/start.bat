@echo off
cd /d "%~dp0"
py -m pip install -q -r requirements.txt
py upload.py
pause
