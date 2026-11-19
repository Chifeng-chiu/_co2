@echo off
setlocal
cd /d "%~dp0"

echo.
echo ==========================================
echo   Nand2Tetris VM Translator - Web Demo
echo ==========================================
echo.

py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 (
  py -3 web_demo.py
  goto :done
)

python -c "import sys" >nul 2>nul
if not errorlevel 1 (
  python web_demo.py
  goto :done
)

echo Python 3 was not found.
echo Please install Python 3 and try again.
echo.
pause
exit /b 1

:done
if errorlevel 1 (
  echo.
  echo The web demo could not start.
  echo Check the error message above.
  echo.
  pause
)
endlocal
