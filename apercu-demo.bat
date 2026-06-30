@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Apercu (demo)
echo ============================================================
echo   APERCU (mode demonstration - donnees fictives, sans reseau)
echo ============================================================
echo.

set "PYEXE="
where py >nul 2>nul && set "PYEXE=py"
if not defined PYEXE (
  where python >nul 2>nul && set "PYEXE=python"
)

if not defined PYEXE (
  echo [ERREUR] Python n'a pas ete trouve.
  echo Installe-le depuis https://www.python.org/downloads/
  echo en cochant "Add python.exe to PATH", puis redemarre l'ordinateur.
  echo.
  pause
  exit /b 1
)

echo Python detecte ^(%PYEXE%^) :
%PYEXE% --version
echo.

if not exist "requirements.txt" (
  echo [ERREUR] Fichiers du projet incomplets.
  echo Telecharge le projet COMPLET ^("Code" puis "Download ZIP"^) et extrais le ZIP.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Premiere utilisation : installation des composants...
  %PYEXE% -m venv .venv
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
) else (
  call ".venv\Scripts\activate.bat"
)

echo.
python -m src.main --demo
echo.
echo ============================================================
echo  Termine. Le tableau de bord de demonstration s'est ouvert.
echo ============================================================
pause
