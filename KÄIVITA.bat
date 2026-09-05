@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title Õppetekst - PowerPoint

echo ============================================================
echo   ÕPPETEKST - POWERPOINT
echo ============================================================
echo.
echo Rakendus käivitatakse sinu arvutis lokaalselt.
echo Kui kõik on korras, avaneb see automaatselt veebilehitsejas.
echo.

call :FIND_PYTHON

if not defined PYTHON_MODE (
    echo Pythonit ei leitud. Proovin Python 3.12 automaatselt paigaldada...
    echo.
    where winget >nul 2>&1
    if errorlevel 1 goto NO_PYTHON

    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto NO_PYTHON

    call :FIND_PYTHON
    if not defined PYTHON_MODE goto NO_PYTHON
)

if not exist ".venv\Scripts\python.exe" (
    echo Esmakordne käivitus: loon rakendusele kohaliku töökeskkonna...
    call :CREATE_VENV
    if errorlevel 1 goto ERROR_EXIT
)

if not exist ".venv\PAKETID_PAIGALDATUD" (
    echo.
    echo Esmakordne käivitus: paigaldan vajalikud komponendid.
    echo Seda tehakse ainult esimesel käivitamisel.
    echo.
    ".venv\Scripts\python.exe" -m pip install --upgrade pip --disable-pip-version-check
    if errorlevel 1 goto ERROR_EXIT
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt --disable-pip-version-check
    if errorlevel 1 goto ERROR_EXIT
    type nul > ".venv\PAKETID_PAIGALDATUD"
)

echo.
echo ------------------------------------------------------------
echo Rakendus käivitub. Ära sulge seda akent kasutamise ajal.
echo Sulgemiseks vajuta siin Ctrl+C või pane see aken kinni.
echo Kui veebilehitseja ise ei avane, mine aadressile:
echo http://localhost:8501
echo ------------------------------------------------------------
echo.

".venv\Scripts\python.exe" -m streamlit run app.py --server.headless false --server.address localhost --server.port 8501
goto END

:FIND_PYTHON
set "PYTHON_MODE="
set "PYTHON_EXE="
where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_MODE=launcher"
    goto :eof
)
where python >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_MODE=exe"
    set "PYTHON_EXE=python"
    goto :eof
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PYTHON_MODE=exe"
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    goto :eof
)
if exist "%ProgramFiles%\Python312\python.exe" (
    set "PYTHON_MODE=exe"
    set "PYTHON_EXE=%ProgramFiles%\Python312\python.exe"
    goto :eof
)
goto :eof

:CREATE_VENV
if /I "%PYTHON_MODE%"=="launcher" (
    py -3 -m venv .venv
    if errorlevel 1 exit /b 1
    exit /b 0
)
if /I "%PYTHON_MODE%"=="exe" (
    "%PYTHON_EXE%" -m venv .venv
    if errorlevel 1 exit /b 1
    exit /b 0
)
exit /b 1

:NO_PYTHON
echo.
echo ============================================================
echo Pythoni automaatne paigaldamine ei õnnestunud.
echo Avan Python 3 allalaadimislehe.
echo Paigalda Python ja tee pärast seda KÄIVITA.bat failil uuesti topeltklõps.
echo ============================================================
start "" "https://www.python.org/downloads/windows/"
pause
goto END

:ERROR_EXIT
echo.
echo ============================================================
echo Käivitamisel tekkis viga.
echo Ära sulge seda akent enne, kui oled veateatest vajadusel pildi teinud.
echo ============================================================
pause

:END
endlocal
