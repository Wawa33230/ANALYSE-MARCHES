# Note de reprise — Veille Appels d'Offres ADOMSENIOR

> À lire en début de prochaine session pour reprendre le fil sans tout réexpliquer.
> Dernière mise à jour : 28/07/2026.

## 1. Contexte
- **Entreprise** : ADOMSENIOR (entité **LYES SANITAIRE / ETS OUHADDAD**), 2 impasse Joliot Curie, 64110 Jurançon.
- **Interlocuteur** : **Loyk DUPORGE**, Directeur des opérations — `loyk.duporge@adomsenior.fr`.
- **Métier** : remplacement **baignoire → douche**, adaptation **PMR** / maintien à domicile,
  pose de **panneaux muraux** (pas de carrelage), pour **bailleurs sociaux**.
- **But de l'outil** : détecter automatiquement les appels d'offres pertinents et prévenir par e-mail.
  Ambition affichée : équivalent d'un outil payant type **DoubleTrade**.

## 2. Dépôt & branche
- Repo : **`Wawa33230/ANALYSE-MARCHES`** — branche de travail : **`claude/tool-operational-integrations-hf6lod`**
  (contient tout l'historique de l'ancienne branche `claude/tender-search-tool-setup-x65gpm`).
- L'outil tourne **sur le PC de Loyk** (Windows), pas dans le cloud.

## 3. Ce qui est FAIT et OPÉRATIONNEL ✅
- **Collecte multi-sources** : BOAMP (API), TED, AWS/marches-publics.info, e-marchespublics
  (scraper), + **lecture des alertes e-mail des plateformes** (IMAP, libellé Gmail
  « Notifications AO »).
- **Scoring / filtrage** métier (mots-clés, CPV, bailleurs, exclusions) → `config.yaml`.
- **Tableau de bord HTML** avec **suivi de statut par marché** (Nouveau / À étudier /
  GO / Déposé / No-go / Écarté — persistant via localStorage, filtre « À traiter »).
- **E-MAIL UNIQUE** (28/07) : le récap ET les « actions à réaliser » partent dans **un seul
  e-mail** (`email.email_unique: true`). Avant : 2 mails, dont un se perdait.
- **Pièce jointe en ZIP** (28/07) : le tableau de bord est joint en `.zip` — un `.html`
  brut avec JavaScript était vraisemblablement filtré par Gmail (cause du « récap non reçu »).
- **Étoile ⭐ Gmail = action traitée** ; lien direct vers l'e-mail d'origine dans chaque
  action ; rappel tant que non étoilé. Détection d'étoile robustifiée (FLAGS avant/après corps).
- **Tâche planifiée fiabilisée** (28/07) : `installer-tache-hebdo.bat` propose
  **quotidien (recommandé) ou hebdo**, et active via PowerShell : **rattrapage d'un
  démarrage manqué** (StartWhenAvailable), réveil (WakeToRun), batterie, 3 réessais.
  → règle le « pas lancé lundi 8h00 ».
- **`diagnostic.bat`** (28/07) : vérifie tâche planifiée, config, mot de passe, IMAP,
  SMTP + envoie un e-mail de test. Journaux : `data/journal-envois.log` (chaque envoi),
  `data/derniere-execution.txt`, `veille-hebdo.log` (rotation > 1 Mo).
- **`mettre-a-jour.bat`** (28/07) : télécharge le ZIP de la branche, remplace les fichiers
  en conservant mot de passe / data / output, sauvegarde `config-precedente.yaml`, et
  **re-pointe la tâche planifiée** (une tâche cassée après re-téléchargement = plus possible).
- **Ouverture à toutes les plateformes** (28/07) : quand on lit un libellé dédié, TOUS les
  e-mails du libellé sont pris (le filtre Gmail fait foi) → ajouter une plateforme = ajouter
  son domaine au filtre Gmail, zéro modif de l'outil. ~20 domaines connus (labels).
- **`GUIDE-PLATEFORMES.md`** (28/07) : plan de couverture complet, plateforme par
  plateforme, avec les alertes à créer et les domaines à ajouter au filtre Gmail.
- Code retour `2` si l'e-mail n'est pas parti (visible dans le Planificateur / log).

## 4. Réglages e-mail (déjà en place)
- Google Workspace `adomsenior.fr` ; IMAP `imap.gmail.com:993`, SMTP `smtp.gmail.com:587` (STARTTLS).
- Compte lu/expéditeur/destinataire : **`loyk.duporge@adomsenior.fr`**.
- **Mot de passe d'application** Google → fichier local **`motdepasse-mail.txt`** (gitignoré),
  ou variable `VEILLE_SMTP_PASSWORD`. Ne JAMAIS le demander/stocker dans le chat.
- **Filtre Gmail** : expéditeurs plateformes → Archiver + lu + libellé `Notifications AO`.

## 5. Points EN ATTENTE / à suivre ⏳
1. **Mettre à jour le PC de Loyk** : re-télécharger UNE dernière fois le ZIP de la branche
   `claude/tool-operational-integrations-hf6lod` (ensuite `mettre-a-jour.bat` suffira),
   puis relancer `installer-tache-hebdo.bat` (choix quotidien/hebdo + rattrapage),
   puis `diagnostic.bat` pour tout vérifier.
2. **Google Workspace en fin d'essai** (~fin juillet 2026) → doit être activé/payé sinon
   IMAP + envoi se coupent (le diagnostic le montrera en ERREUR).
3. **Créer les alertes plateformes** selon `GUIDE-PLATEFORMES.md` (AWS, e-marchespublics,
   PLACE, Maximilien, marches-securises en priorité). Règle d'or : 1 alerte = 1 mot-clé.
4. **achatpublic** : pas d'alerte nouveautés (confirmé par leur support) → couvert par
   BOAMP + relance manuelle occasionnelle.
5. Vérifier après une semaine : `data/journal-envois.log` et que le récap arrive bien
   (sinon regarder SPAM ; la pièce jointe est maintenant zippée pour éviter le filtrage).

## 6. Fichiers clés
- `config.yaml` — sources, scoring, `email:` (dont `email_unique`), `mail_alertes:`
  (dossier, `expediteurs_stricts`, expéditeurs).
- `src/main.py` — orchestration, `--email`, e-mail unique, code retour, dernière exécution.
- `src/notify.py` — SMTP, `send_recap` (actions intégrées + ZIP), `_log_send` → journal.
- `src/diagnostic.py` — vérifications config/IMAP/SMTP + mail de test (`diagnostic.bat`).
- `src/sources/mail_alertes.py` — IMAP, classification opportunité/action, étoile, labels.
- `src/dashboard.py` — tableau de bord + statuts localStorage.
- `installer-tache-hebdo.bat`, `veille-hebdo.bat`, `mettre-a-jour.bat`, `diagnostic.bat`.
- `GUIDE-PLATEFORMES.md`, `VEILLE-AUTOMATIQUE-HEBDO.md` (mode d'emploi complet).

## 7. Comment tester (sur le PC)
```
:: diagnostic complet + mail de test :
diagnostic.bat
:: vraie collecte + envoi :
schtasks /Run /TN "VeilleAO-Hebdo"
```
Puis vérifier `data/derniere-execution.txt` et `data/journal-envois.log`.

## 8. Contraintes de l'environnement Claude (pour l'assistant)
- Le proxy **bloque les sites de marchés publics** (403) → tester le scraping en direct
  est impossible ici ; tester en mode `--demo` et par tests unitaires locaux.
- Le connecteur **Gmail** de la session peut pointer vers `ets.ouhaddad@gmail.com` OU
  `loyk.duporge@adomsenior.fr` — vérifier au début.
- Ne JAMAIS demander / stocker le mot de passe d'application en clair dans le chat.

> Note volontairement limitée à **l'outil de veille marché**.
