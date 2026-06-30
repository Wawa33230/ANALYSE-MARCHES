@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Veille Appels d'Offres
echo ============================================================
echo   VEILLE APPELS D'OFFRES - Salle de bain / Accessibilite PMR
echo ============================================================
echo.

rem --- Choix de l'interpreteur Python : 'py' (recommande sous Windows) sinon 'python'
set "PYEXE="
where py >nul 2>nul && set "PYEXE=py"
if not defined PYEXE (
  where python >nul 2>nul && set "PYEXE=python"
)

if not defined PYEXE (
  echo [ERREUR] Python n'a pas ete trouve sur cet ordinateur.
  echo.
  echo  1. Telecharge Python sur https://www.python.org/downloads/
  echo  2. Pendant l'installation, COCHE la case "Add python.exe to PATH"
  echo  3. Redemarre l'ordinateur, puis relance ce fichier.
  echo.
  pause
  exit /b 1
)

echo Python detecte ^(%PYEXE%^) :
%PYEXE% --version
echo.

rem --- Verifie qu'on est bien dans le dossier complet du projet
if not exist "requirements.txt" (
  echo [ERREUR] Le fichier requirements.txt est introuvable.
  echo Tu as probablement lance ce .bat sans les autres fichiers du projet.
  echo Telecharge le projet COMPLET ^(bouton vert "Code" puis "Download ZIP"^),
  echo extrais le ZIP, puis lance ce fichier depuis le dossier extrait.
  echo.
  pause
  exit /b 1
)

rem --- Premiere utilisation : creation de l'environnement
if not exist ".venv\Scripts\python.exe" (
  echo Premiere utilisation : installation des composants ^(1 a 2 minutes^)...
  %PYEXE% -m venv .venv
  if errorlevel 1 (
    echo [ERREUR] Impossible de creer l'environnement Python. Voir le README.
    pause
    exit /b 1
  )
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
) else (
  call ".venv\Scripts\activate.bat"
)

echo.
echo Recherche des marches en cours...
echo.
python -m src.main

echo.
echo ============================================================
echo  Termine. Le tableau de bord s'est ouvert dans ton navigateur.
echo  (Sinon, ouvre le fichier : output\tableau-de-bord.html)
echo ============================================================
pause
