@echo off
REM Launcher for run_wt.ps1
REM Try PowerShell 7 (pwsh) first, fallback to PowerShell 5.1 (powershell)
cd /d "%~dp0"

where pwsh >nul 2>&1
if %errorlevel% == 0 (
    pwsh -ExecutionPolicy Bypass -File "%~dp0run_wt.ps1"
) else (
    powershell -ExecutionPolicy Bypass -File "%~dp0run_wt.ps1"
)
