@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   APERCU (mode demonstration - donnees fictives, sans reseau)
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERREUR] Python n'a pas ete trouve. Voir le README.
  pause
  exit /b 1
)

if not exist ".venv" (
  echo Premiere utilisation : installation des composants...
  python -m venv .venv
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip >nul
  pip install -r requirements.txt
) else (
  call ".venv\Scripts\activate.bat"
)

echo.
python -m src.main --demo
echo.
pause
