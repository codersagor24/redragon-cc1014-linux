@echo off
set "DAEMON_PATH=%~dp0cooler_display.py"
echo Starting Cooler Display Daemon in background...
start "" pythonw "%DAEMON_PATH%"
echo Started.
