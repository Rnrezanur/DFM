@echo off
title DFM - Download Fast Manager
cd /d "%~dp0"
if exist "target\release\DFM.exe" (
    start "" "target\release\DFM.exe" %*
) else if exist "DFM.exe" (
    start "" "DFM.exe" %*
) else (
    cargo run --release -- %*
)
