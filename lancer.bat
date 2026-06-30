@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   VEILLE APPELS D'OFFRES - Salle de bain / Accessibilite PMR
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERREUR] Python n'a pas ete trouve.
  echo.
  echo  1. Telecharge Python sur https://www.python.org/downloads/
  echo  2. Pendant l'installation, COCHE la case "Add Python to PATH"
  echo  3. Relance ce fichier.
  echo.
  pause
  exit /b 1
)

if not exist ".venv" (
  echo Premiere utilisation : installation des composants ^(1 a 2 minutes^)...
  python -m venv .venv
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip >nul
  pip install -r requirements.txt
) else (
  call ".venv\Scripts\activate.bat"
)

echo.
python -m src.main
echo.
pause
