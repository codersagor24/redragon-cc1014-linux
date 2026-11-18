@echo off
set "PID_FILE=%APPDATA%\cooler-display\cooler-display.pid"

if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    if defined PID (
        echo Stopping PID !PID!...
        taskkill /F /PID !PID! >nul 2>&1
        del "%PID_FILE%" >nul 2>&1
    )
)

:: Also terminate any pythonw process running cooler_display.py
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*cooler_display.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

echo Cooler Display Daemon stopped.
