@echo off
rem ============================================================
rem  INSTALLE la tache planifiee Windows "VeilleAO-Hebdo"
rem  -> lance la veille automatiquement (tous les jours a 08:00
rem     par defaut, ou chaque lundi) et envoie le mail.
rem  Double-clique simplement sur ce fichier (une seule fois).
rem
rem  FIABILITE : la tache est reglee pour
rem   - RATTRAPER une execution manquee (PC eteint a 8h00 -> elle
rem     se lance des que le PC est rallume) ;
rem   - REVEILLER le PC s'il est en veille ;
rem   - tourner meme sur batterie (portable) ;
rem   - reessayer 3 fois en cas d'echec (toutes les 10 min).
rem ============================================================
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Installation de la veille automatique

echo ============================================================
echo   INSTALLATION - Veille automatique des appels d'offres
echo ============================================================
echo.

rem --- 1) Mot de passe d'application Gmail (stocke en local, jamais sur GitHub) ---
rem  NB : expansion differee (!MDP!) obligatoire, sinon la variable saisie dans un
rem       bloc ( ) est lue AVANT la saisie (bug classique des .bat Windows).
if exist "motdepasse-mail.txt" (
  echo [OK] Un mot de passe d'application est deja enregistre ^(motdepasse-mail.txt^).
  echo      Pour le changer, supprime ce fichier puis relance cet installateur.
) else (
  echo Pour envoyer l'e-mail, il faut un "mot de passe d'application" Gmail
  echo ^(16 caracteres^). Procedure detaillee : VEILLE-AUTOMATIQUE-HEBDO.md
  echo.
  set /p "MDP=Colle ici le mot de passe d'application (ou laisse vide pour plus tard) : "
  if not "!MDP!"=="" (
    rem  On enleve les espaces eventuels du code (Google l'affiche par blocs de 4).
    set "MDP=!MDP: =!"
    > "motdepasse-mail.txt" echo !MDP!
    echo [OK] Mot de passe enregistre dans motdepasse-mail.txt ^(reste sur ton PC^).
  ) else (
    echo [i] Aucun mot de passe saisi : cree le fichier motdepasse-mail.txt plus tard.
  )
)
echo.

rem --- 2) Frequence : quotidien (recommande) ou hebdomadaire ---
echo Pour ne RATER AUCUN MARCHE, le mieux est une veille QUOTIDIENNE (8h00).
echo (L'e-mail met en avant uniquement les NOUVEAUTES : pas de doublons.)
echo.
set "FREQ=Q"
set /p "FREQ=Frequence ? Q = tous les jours (recommande) / H = lundi seulement [Q] : "
echo.

rem --- 3) Creation de la tache planifiee ---
if /I "!FREQ!"=="H" (
  schtasks /Create /SC WEEKLY /D MON /ST 08:00 /F ^
    /TN "VeilleAO-Hebdo" ^
    /TR "\"%~dp0veille-hebdo.bat\""
) else (
  schtasks /Create /SC DAILY /ST 08:00 /F ^
    /TN "VeilleAO-Hebdo" ^
    /TR "\"%~dp0veille-hebdo.bat\""
)

if errorlevel 1 (
  echo.
  echo [ERREUR] Impossible de creer la tache planifiee.
  echo Astuce : fais un CLIC DROIT sur ce fichier et "Executer en tant qu'administrateur".
  echo.
  pause
  exit /b 1
)

rem --- 4) Reglages de FIABILITE (rattrapage, sortie de veille, reessais) ---
rem  C'est CE reglage qui evite de "rater le lundi 8h00" : si le PC etait
rem  eteint ou en veille a l'heure prevue, Windows lance la tache au demarrage.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 10); Set-ScheduledTask -TaskName 'VeilleAO-Hebdo' -Settings $s | Out-Null"

if errorlevel 1 (
  echo [ATTENTION] Reglages avances non appliques ^(la tache existe quand meme^).
  echo Ouvre le Planificateur de taches -^> VeilleAO-Hebdo -^> Parametres et coche
  echo "Executer la tache des que possible apres un demarrage manque".
) else (
  echo [OK] Rattrapage automatique active : PC eteint a 8h00 = la veille se
  echo      lancera automatiquement au prochain demarrage du PC.
)

echo.
echo ============================================================
if /I "!FREQ!"=="H" (
  echo  [OK] Tache "VeilleAO-Hebdo" installee : chaque LUNDI a 08h00.
) else (
  echo  [OK] Tache "VeilleAO-Hebdo" installee : TOUS LES JOURS a 08h00.
)
echo  - Pour tester tout de suite : double-clique sur diagnostic.bat
echo  - Pour forcer une execution : schtasks /Run /TN "VeilleAO-Hebdo"
echo  - Pour desinstaller : double-clique sur desinstaller-tache-hebdo.bat
echo ============================================================
echo.
pause
