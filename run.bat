@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   AGY Token Real-time Desktop Monitor
echo ===================================================

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

:: Check if requirements are installed
python -c "import PySide6, watchdog" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing required dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install requirements!
        pause
        exit /b 1
    )
)

:: Launch the application
if "%1"=="--console" (
    echo [INFO] Starting in console mode...
    python src\main.py
) else (
    echo [INFO] Starting AGY Token Monitor in background...
    start "" pythonw src\main.py
)

endlocal
