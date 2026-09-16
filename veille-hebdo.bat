@echo off
rem ============================================================
rem  VEILLE AO - Execution HEBDOMADAIRE AUTOMATIQUE (silencieuse)
rem  Lance la collecte SANS ouvrir le navigateur et ENVOIE le
rem  recapitulatif par e-mail. Appele par la tache planifiee
rem  Windows (voir installer-tache-hebdo.bat). Tout est journalise
rem  dans veille-hebdo.log.
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"

rem --- Rotation du journal (au-dela de 1 Mo on archive et on repart a zero) ---
if exist "veille-hebdo.log" (
  for %%A in ("veille-hebdo.log") do if %%~zA GTR 1048576 (
    copy /Y "veille-hebdo.log" "veille-hebdo.ancien.log" >nul
    type nul > "veille-hebdo.log"
  )
)

set "PYEXE="
where py >nul 2>nul && set "PYEXE=py"
if not defined PYEXE (
  where python >nul 2>nul && set "PYEXE=python"
)
if not defined PYEXE (
  echo [%date% %time%] ERREUR : Python introuvable. >> "veille-hebdo.log"
  exit /b 1
)

rem --- Cree l'environnement au 1er passage, sinon l'active ---
if not exist ".venv\Scripts\python.exe" (
  %PYEXE% -m venv .venv >> "veille-hebdo.log" 2>&1
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip >> "veille-hebdo.log" 2>&1
  python -m pip install -r requirements.txt >> "veille-hebdo.log" 2>&1
) else (
  call ".venv\Scripts\activate.bat"
)

rem --- Auto-reparation des dependances : si une librairie de requirements.txt
rem     manque dans le .venv (typiquement 'anthropic', ajoute apres coup pour
rem     l'agent IA), on (re)installe requirements.txt. Idempotent : si tout est
rem     deja present, cette verification ne fait rien (aucun cout, ~1 seconde).
python -c "import anthropic, yaml, requests" >nul 2>nul
if errorlevel 1 (
  echo [%date% %time%] Dependances manquantes detectees -> installation... >> "veille-hebdo.log"
  python -m pip install -r requirements.txt >> "veille-hebdo.log" 2>&1
)

echo [%date% %time%] --- Lancement de la veille hebdomadaire --- >> "veille-hebdo.log"
python -m src.main --no-open --email >> "veille-hebdo.log" 2>&1
echo [%date% %time%] --- Termine (code %errorlevel%) --- >> "veille-hebdo.log"
exit /b %errorlevel%
