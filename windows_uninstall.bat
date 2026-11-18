@echo off
echo ======================================================
echo   Cooler Display Driver - Windows Uninstaller
echo ======================================================
echo.

echo [1/3] Stopping running processes...
call "%~dp0windows_stop.bat"

echo [2/3] Removing Windows Auto-Start...
set "VBS_SCRIPT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\cooler-display-autostart.vbs"
if exist "%VBS_SCRIPT%" del /f /q "%VBS_SCRIPT%"

echo [3/3] Removing configuration...
set "CONF_DIR=%APPDATA%\cooler-display"
if exist "%CONF_DIR%" rmdir /s /q "%CONF_DIR%"

echo.
echo [OK] Uninstallation complete.
pause
