@echo off
REM Change to your project directory
cd /d D:\office\software\restaurant

REM Activate your virtual environment
call .venv\Scripts\activate.bat

REM Run the server
python run_server.py

REM Keep the window open (optional)
pause
