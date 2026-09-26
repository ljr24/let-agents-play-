@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Missing local Python environment: .venv
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -B -m daylab %*
if errorlevel 1 (
  echo The experiment stopped. Please copy the error above.
  pause
)
endlocal
