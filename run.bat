@echo off
REM Run the Hand Gesture Control app with the virtual environment

cd /d "%~dp0"
call venv\Scripts\activate.bat
python app.py
pause
