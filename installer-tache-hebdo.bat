@echo off
rem ============================================================
rem  INSTALLE la tache planifiee Windows "VeilleAO-Hebdo"
rem  -> lance la veille TOUS LES LUNDIS a 08:00 et envoie le mail.
rem  Double-clique simplement sur ce fichier (une seule fois).
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title Installation de la veille hebdomadaire

echo ============================================================
echo   INSTALLATION - Veille automatique une fois par semaine
echo ============================================================
echo.
echo Cette tache lancera la recherche de marches CHAQUE LUNDI a 08h00
echo et t'enverra un e-mail avec les consultations interessantes.
echo.

rem --- 1) Mot de passe d'application Gmail (stocke en local, jamais sur GitHub) ---
if exist "motdepasse-mail.txt" (
  echo [OK] Un mot de passe d'application est deja enregistre ^(motdepasse-mail.txt^).
  echo      Pour le changer, supprime ce fichier puis relance cet installateur.
) else (
  echo Pour envoyer l'e-mail, il faut un "mot de passe d'application" Gmail
  echo ^(16 caracteres^). Procedure detaillee : VEILLE-AUTOMATIQUE-HEBDO.md
  echo.
  set /p MDP="Colle ici le mot de passe d'application (ou laisse vide pour plus tard) : "
  if not "%MDP%"=="" (
    > "motdepasse-mail.txt" echo %MDP%
    echo [OK] Mot de passe enregistre dans motdepasse-mail.txt ^(ce fichier reste sur ton PC^).
  ) else (
    echo [i] Aucun mot de passe saisi : cree le fichier motdepasse-mail.txt plus tard.
  )
)
echo.

rem --- 2) Creation de la tache planifiee ---
schtasks /Create /SC WEEKLY /D MON /ST 08:00 /F ^
  /TN "VeilleAO-Hebdo" ^
  /TR "\"%~dp0veille-hebdo.bat\""

if errorlevel 1 (
  echo.
  echo [ERREUR] Impossible de creer la tache planifiee.
  echo Astuce : fais un CLIC DROIT sur ce fichier et "Executer en tant qu'administrateur".
  echo.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  [OK] Tache "VeilleAO-Hebdo" installee : chaque LUNDI a 08h00.
echo  - Pour tester tout de suite : schtasks /Run /TN "VeilleAO-Hebdo"
echo  - Pour desinstaller : double-clique sur desinstaller-tache-hebdo.bat
echo ============================================================
echo.
pause
