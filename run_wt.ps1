# BLE RF Test Studio - Windows Terminal Launcher

# Check if already in Windows Terminal
if ($env:WT_SESSION) {
    # Already in WT, run the app
    Write-Host "========================================"
    Write-Host "   BLE RF Test Studio (Windows Terminal)"
    Write-Host "========================================"
    Write-Host ""

    # Check virtual environment
    if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
        Write-Host "[Error] Virtual environment not found!"
        Write-Host "Please run setup.bat first"
        Read-Host "Press Enter to exit"
        exit 1
    }

    # Activate virtual environment
    & "venv\Scripts\Activate.ps1"

    Write-Host "[Info] Starting application..."
    Write-Host ""

    # Run with unbuffered mode
    python -u src/main.py

    Write-Host ""
    Write-Host "[Program exited]"
    Read-Host "Press Enter to exit"
}
else {
    # Not in WT, try to launch with wt
    $wtPath = Get-Command wt -ErrorAction SilentlyContinue
    if ($wtPath) {
        # Get script path
        $scriptPath = $MyInvocation.MyCommand.Path
        Set-Location (Split-Path $scriptPath)

        # Check if pwsh (PowerShell 7) is available, fallback to powershell (5.1)
        $pwshPath = Get-Command pwsh -ErrorAction SilentlyContinue
        if ($pwshPath) {
            $psCmd = "pwsh"
        } else {
            $psCmd = "powershell"
        }

        # Launch in Windows Terminal
        # -w 0: use most recent window (or create new if none exists)
        # --title: set tab title
        wt -w 0 new-tab --title "TestStudio" -d . $psCmd -NoExit -File $scriptPath
    }
    else {
        Write-Host "[Warning] Windows Terminal not found, running in current terminal..."
        # Re-run with WT_SESSION set to simulate being in WT
        $env:WT_SESSION = "1"
        & $MyInvocation.MyCommand.Path
    }
}
