@echo off
rem ============================================================
rem  DIAGNOSTIC de la veille : verifie que TOUT fonctionne.
rem   1. La tache planifiee existe-t-elle ? Quand tourne-t-elle ?
rem   2. Config / mot de passe / IMAP (lecture) / SMTP (envoi)
rem   3. Envoi d'un e-mail de TEST
rem  Double-clique sur ce fichier quand quelque chose semble
rem  ne pas marcher (mail non recu, tache non lancee...).
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title Diagnostic - Veille appels d'offres

echo ============================================================
echo   1/3 - TACHE PLANIFIEE WINDOWS
echo ============================================================
schtasks /Query /TN "VeilleAO-Hebdo" /V /FO LIST 2>nul | findstr /C:"Nom de la t" /C:"TaskName" /C:"Prochaine" /C:"Next Run" /C:"Dernier r" /C:"Last Result" /C:"Derni" /C:"Last Run" /C:"Statut" /C:"Status" /C:"cuter" /C:"Task To Run"
if errorlevel 1 (
  echo [ERREUR] La tache "VeilleAO-Hebdo" N'EXISTE PAS sur ce PC.
  echo          -^> double-clique sur installer-tache-hebdo.bat pour la creer.
) else (
  echo.
  echo [i] "Dernier resultat : 0" = la derniere execution s'est bien passee.
  echo     "267011" = la tache n'a encore jamais tourne.
  echo     "0x2"    = execution OK mais l'E-MAIL n'est pas parti ^(voir data\journal-envois.log^).
)
if exist "data\derniere-execution.txt" (
  echo.
  type "data\derniere-execution.txt"
)

echo.
echo ============================================================
echo   2/3 et 3/3 - CONFIG, LECTURE GMAIL, ENVOI + E-MAIL DE TEST
echo ============================================================

set "PYEXE="
if exist ".venv\Scripts\python.exe" set "PYEXE=.venv\Scripts\python.exe"
if not defined PYEXE ( where py >nul 2>nul && set "PYEXE=py" )
if not defined PYEXE ( where python >nul 2>nul && set "PYEXE=python" )
if not defined PYEXE (
  echo [ERREUR] Python introuvable sur ce PC. Installe-le depuis python.org
  echo          en cochant "Add Python to PATH".
  pause
  exit /b 1
)

%PYEXE% -m src.diagnostic --envoi-test

echo.
echo ------------------------------------------------------------
echo  Journal des envois d'e-mails : data\journal-envois.log
echo  Journal des executions auto  : veille-hebdo.log
echo ------------------------------------------------------------
pause
