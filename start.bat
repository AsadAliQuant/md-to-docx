@echo off
setlocal enabledelayedexpansion
REM One-click launcher for md-to-docx
cd /d "%~dp0"

REM Check pandoc; auto-install via winget if it's missing
where pandoc >nul 2>&1
if errorlevel 1 (
    echo [!] Pandoc not found.
    where winget >nul 2>&1
    if errorlevel 1 (
        echo [!] winget is not available on this PC either.
        echo     Install Pandoc manually: https://pandoc.org/installing.html
        pause
        exit /b 1
    )

    echo [*] Installing Pandoc via winget - this may take a minute...
    winget install --id JohnMacFarlane.Pandoc -e --silent --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo [!] Automatic install failed ^(try running this .bat as Administrator^).
        echo     Or install manually: winget install --id JohnMacFarlane.Pandoc
        pause
        exit /b 1
    )

    echo [*] Pandoc installed. Refreshing PATH for this session...
    REM winget updates the registry's PATH, but this already-running cmd session
    REM won't see it until we reload it from the registry (avoids needing a restart).
    for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SysPath=%%B"
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "UserPath=%%B"
    set "PATH=!SysPath!;!UserPath!"

    where pandoc >nul 2>&1
    if errorlevel 1 (
        echo [!] Pandoc installed but not visible in this terminal yet.
        echo     Close this window and run start.bat again.
        pause
        exit /b 1
    )
    echo [*] Pandoc is ready.
)

REM First run: create venv + install Flask
if not exist "venv\Scripts\python.exe" (
    echo [*] Setting up virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.
echo [*] Starting server at http://127.0.0.1:5000
start "" http://127.0.0.1:5000
python app.py
