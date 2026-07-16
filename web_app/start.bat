@echo off
REM Gesture Control Web Application Startup Script
REM This script starts the Flask web application

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║    Gesture Control System - Web Application            ║
echo ║    Starting Flask Server...                            ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "app_web.py" (
    echo ❌ ERROR: app_web.py not found!
    echo Make sure you're running this script from the web_app directory
    pause
    exit /b 1
)

REM Install/Update requirements
echo 📦 Checking dependencies...
pip install -r requirements.txt -q

if errorlevel 1 (
    echo ❌ ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo ✅ Dependencies installed successfully!
echo.

REM Start the Flask app
echo 🚀 Starting Flask application...
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║  Web Application is starting...                        ║
echo ║                                                        ║
echo ║  📍 URL: http://127.0.0.1:5000                        ║
echo ║  📍 Access from phone: http://[YOUR-IP]:5000          ║
echo ║                                                        ║
echo ║  Press CTRL+C to stop the server                       ║
echo ╚════════════════════════════════════════════════════════╝
echo.

python app_web.py

if errorlevel 1 (
    echo.
    echo ❌ ERROR: Flask application crashed
    echo Check the error message above
    pause
    exit /b 1
)

pause
