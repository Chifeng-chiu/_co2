@echo off
setlocal
cd /d "%~dp0"

rem Launch the graphical front end without a console window when possible.
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw -m jackc.gui
    exit /b 0
)

rem Fallback: run with the normal interpreter so errors are visible.
python -m jackc.gui
if errorlevel 1 pause
endlocal
