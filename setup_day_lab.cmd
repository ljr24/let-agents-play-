@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install pygame==2.6.1
if errorlevel 1 goto failed
echo Setup complete. Double-click start_day_lab.cmd to play.
pause
exit /b 0
:failed
echo Setup failed. Install Python 3.12 with the Python Launcher, then retry.
pause
exit /b 1
