@echo off
REM Change to your project directory
cd /d D:\restaurant

REM Activate your virtual environment
call .venv\Scripts\activate.bat

REM Run the Django app via Waitress using your Python script
python run_server.py
