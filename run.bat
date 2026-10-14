@echo off
title AI Search Agent Launcher
echo ========================================================
echo       Launching AI Search Agent Platform
echo ========================================================
echo Activating virtual environment...
call "google-search-agent\venv\Scripts\activate.bat"
python start_app.py
pause
