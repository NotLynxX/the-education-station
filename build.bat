@echo off
cd /d "%~dp0"
python build.py
if errorlevel 1 (
  py build.py
)
echo.
pause
