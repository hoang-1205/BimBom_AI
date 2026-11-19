@echo off
setlocal
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"
if not exist "%~dp0Model_BimBomAI\.venv\Scripts\python.exe" (
  echo Khong tim thay Python. Chay Model_BimBomAI\setup.ps1 truoc.
  exit /b 1
)
"%~dp0Model_BimBomAI\.venv\Scripts\python.exe" -B "%~dp0Run_BimBom.py" %*
exit /b %errorlevel%
