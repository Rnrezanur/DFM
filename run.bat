@echo off
title DFM - Download Fast Manager
cd /d "%~dp0"
"C:\Users\hunte\AppData\Local\Programs\Python\Python312\pythonw.exe" main.py %*
if %ERRORLEVEL% NEQ 0 (
    "C:\Users\hunte\AppData\Local\Programs\Python\Python312\python.exe" main.py %*
)
