@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Calibrage des filtres (analyse 5 ans)
echo ============================================================
echo   CALIBRAGE DES FILTRES - analyse 5 ans des bailleurs
echo   (outil d'analyse : sert a affiner le tableau de bord)
echo ============================================================
echo.

set "PYEXE="
where py >nul 2>nul && set "PYEXE=py"
if not defined PYEXE (
  where python >nul 2>nul && set "PYEXE=python"
)
if not defined PYEXE (
  echo [ERREUR] Python introuvable. Voir le README.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Premiere utilisation : installation des composants...
  %PYEXE% -m venv .venv
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip >nul
  python -m pip install -r requirements.txt
) else (
  call ".venv\Scripts\activate.bat"
)

echo.
echo Analyse en cours (2 a 5 minutes selon le nombre de bailleurs)...
echo.
python -m src.calibration
echo.
echo ============================================================
echo  Termine. Envoie-moi le fichier : data\calibration-bailleurs.json
echo  pour que je regle les filtres du tableau de bord.
echo ============================================================
pause
