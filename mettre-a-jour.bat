@echo off
rem ============================================================
rem  MISE A JOUR de l'outil de veille en 1 double-clic.
rem  Telecharge la derniere version depuis GitHub et remplace les
rem  fichiers du dossier EN CONSERVANT :
rem    - motdepasse-mail.txt   (ton mot de passe d'application)
rem    - data\  et  output\    (historique et tableaux)
rem  L'ancien config.yaml est garde en copie : config-precedente.yaml
rem  La tache planifiee est re-pointee vers ce dossier (plus de
rem  tache cassee apres un re-telechargement du ZIP a la main).
rem ============================================================
chcp 65001 >nul

rem  On se relance depuis %TEMP% pour pouvoir remplacer CE fichier lui-meme.
if "%~1"=="" (
  copy /Y "%~f0" "%TEMP%\veille-maj.bat" >nul
  start "Mise a jour - Veille AO" cmd /k ""%TEMP%\veille-maj.bat" "%~dp0""
  exit
)
cd /d "%~1"
title Mise a jour - Veille AO

set "BRANCHE=main"
set "ZIPURL=https://codeload.github.com/Wawa33230/ANALYSE-MARCHES/zip/refs/heads/%BRANCHE%"

echo ============================================================
echo   MISE A JOUR - Outil de veille appels d'offres
echo ============================================================
echo.
echo Telechargement de la derniere version depuis GitHub ...
del "%TEMP%\veille-maj.zip" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { Invoke-WebRequest -Uri '%ZIPURL%' -OutFile '%TEMP%\veille-maj.zip' -UseBasicParsing } catch { exit 1 }"
if not exist "%TEMP%\veille-maj.zip" goto :manuel

echo Decompression ...
rmdir /S /Q "%TEMP%\veille-maj-dossier" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -Path '%TEMP%\veille-maj.zip' -DestinationPath '%TEMP%\veille-maj-dossier' -Force"
set "SRC="
for /d %%D in ("%TEMP%\veille-maj-dossier\*") do set "SRC=%%D"
if not defined SRC goto :manuel

echo Remplacement des fichiers (mot de passe, data et output conserves) ...
if exist "config.yaml" copy /Y "config.yaml" "config-precedente.yaml" >nul
robocopy "%SRC%" "%CD%" /E /XF motdepasse-mail.txt /XD data output .venv >nul
if errorlevel 8 goto :manuel

rem  Re-pointe la tache planifiee vers CE dossier (si elle existe).
schtasks /Query /TN "VeilleAO-Hebdo" >nul 2>nul
if not errorlevel 1 (
  schtasks /Change /TN "VeilleAO-Hebdo" /TR "\"%CD%\veille-hebdo.bat\"" >nul
  echo [OK] Tache planifiee re-pointee vers ce dossier.
) else (
  echo [i] Aucune tache planifiee trouvee : lance installer-tache-hebdo.bat pour l'ajouter.
)

rmdir /S /Q "%TEMP%\veille-maj-dossier" 2>nul
del "%TEMP%\veille-maj.zip" 2>nul

echo.
echo ============================================================
echo  [OK] MISE A JOUR TERMINEE.
echo  - Ton ancien config.yaml est conserve : config-precedente.yaml
echo    (si tu y avais fait des reglages perso, recopie-les dans config.yaml)
echo  - Conseil : double-clique sur diagnostic.bat pour tout verifier.
echo ============================================================
echo.
pause
exit

:manuel
echo.
echo ============================================================
echo  [ERREUR] Telechargement automatique impossible (depot prive
echo  ou pas d'internet). MISE A JOUR MANUELLE en 3 etapes :
echo   1. Va sur github.com/Wawa33230/ANALYSE-MARCHES , choisis la
echo      branche "%BRANCHE%"
echo      puis Code ^> Download ZIP.
echo   2. Decompresse le ZIP et copie TOUT son contenu DANS ce
echo      dossier (remplace les fichiers existants).
echo   3. Ton motdepasse-mail.txt, data\ et output\ ne sont pas
echo      dans le ZIP : ils restent intacts. Relance ensuite
echo      diagnostic.bat pour verifier.
echo ============================================================
echo.
pause
exit
