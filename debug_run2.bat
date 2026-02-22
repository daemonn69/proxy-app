@echo off
cd /d "%~dp0"
python main.py > crash_log.txt 2>&1
pause
