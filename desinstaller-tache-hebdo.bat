@echo off
rem ============================================================
rem  DESINSTALLE la tache planifiee hebdomadaire "VeilleAO-Hebdo".
rem  (Ne supprime pas tes fichiers ni ton mot de passe.)
rem ============================================================
chcp 65001 >nul
title Desinstallation de la veille hebdomadaire

schtasks /Delete /TN "VeilleAO-Hebdo" /F
if errorlevel 1 (
  echo [i] La tache n'existait pas ^(ou deja supprimee^).
) else (
  echo [OK] Tache hebdomadaire supprimee. Tu peux toujours lancer la veille
  echo      manuellement avec "lancer.bat".
)
echo.
pause
