@echo off
setlocal enabledelayedexpansion

echo ======================================================
echo   Cooler Display Driver - Windows Installer
echo ======================================================
echo.

:: 1. Check Python installation
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.8+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/4] Installing required Python libraries (hidapi, psutil)...
python -m pip install --upgrade pip
python -m pip install hidapi psutil
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)

:: 2. Create AppData configuration
echo [2/4] Initializing configuration directory...
set "CONF_DIR=%APPDATA%\cooler-display"
if not exist "%CONF_DIR%" mkdir "%CONF_DIR%"

set "CONF_FILE=%CONF_DIR%\cooler-display.conf"
if not exist "%CONF_FILE%" (
    (
        echo mode="cpu_temp"
        echo alert_enabled="0"
        echo alert_temp="80"
        echo alert_value="99"
    ) > "%CONF_FILE%"
    echo       Created default config: %CONF_FILE%
)

:: 3. Configure Windows Auto-Start on Login
echo [3/4] Configuring Auto-Start on Windows login...
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS_SCRIPT=%STARTUP_FOLDER%\cooler-display-autostart.vbs"
set "DAEMON_PATH=%~dp0cooler_display.py"

:: Create silent VBS launcher in Startup folder
(
    echo Set WshShell = CreateObject("WScript.Shell"^)
    echo WshShell.Run "pythonw """ ^& "%DAEMON_PATH%" ^& """", 0, False
) > "%VBS_SCRIPT%"
echo       Auto-start registered in Startup folder.

:: 4. Start Driver Now
echo [4/4] Starting Cooler Display Daemon...
start "" pythonw "%DAEMON_PATH%"

echo.
echo ======================================================
echo   [OK] Installation complete!
echo.
echo   * The cooler display is now updating in real time.
echo   * Double-click 'run_gui.bat' to launch the GUI manager.
echo   * The driver will automatically start on Windows boot.
echo ======================================================
echo.
pause
