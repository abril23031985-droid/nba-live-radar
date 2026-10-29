@echo off
cd /d "c:\NBA"
call venv\Scripts\activate.bat
python sync_deploy.py %*
