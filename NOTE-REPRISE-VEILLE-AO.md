# Note de reprise — Veille Appels d'Offres ADOMSENIOR

> À lire en début de prochaine session pour reprendre le fil sans tout réexpliquer.
> Dernière mise à jour : 24/07/2026.

## 1. Contexte
- **Entreprise** : ADOMSENIOR (entité **LYES SANITAIRE / ETS OUHADDAD**), 2 impasse Joliot Curie, 64110 Jurançon.
- **Interlocuteur** : **Loyk DUPORGE**, Directeur des opérations — `loyk.duporge@adomsenior.fr`.
- **Métier** : remplacement **baignoire → douche**, adaptation **PMR** / maintien à domicile,
  pose de **panneaux muraux** (pas de carrelage), pour **bailleurs sociaux**.
- **But de l'outil** : détecter automatiquement les appels d'offres pertinents et prévenir par e-mail.

## 2. Dépôt & branche
- Repo : **`Wawa33230/ANALYSE-MARCHES`** — branche de travail : **`claude/tender-search-tool-setup-x65gpm`**.
- Dernier commit de référence : **`6b48c6a`** (rappel d'actions + étoile Gmail).
- L'outil tourne **sur le PC de Loyk** (Windows), pas dans le cloud. Chemin actuel :
  `C:\Users\dupor\Desktop\CLAUDE\VEILLE AO\ANALYSE-MARCHES-claude-tender-search-tool-setup-x65gpm\`.

## 3. Ce qui est FAIT et OPÉRATIONNEL ✅
- **Collecte multi-sources** : BOAMP (API Opendatasoft), TED, AWS/marches-publics.info,
  e-marchespublics (scraper), + **lecture des alertes e-mail des plateformes** (IMAP).
- **Scoring / filtrage** ciblé métier (mots-clés, CPV, bailleurs, exclusions) → `config.yaml`.
- **Tableau de bord HTML** (`output/tableau-de-bord.html`).
- **Récap hebdomadaire par e-mail** (`src/notify.py`) : prioritaires + à regarder, nouveautés
  surlignées, tableau joint. Envoyé via SMTP Gmail/Workspace.
- **Lecture des alertes plateformes** (`src/sources/mail_alertes.py`) : lit le **label Gmail
  « Notifications AO »** en IMAP, extrait les consultations (titre, réf, acheteur, date limite),
  gère le format achatpublic (prose) et les digests (liens), dates FR + ISO.
- **Tri opportunité vs action** :
  - *nouvelle consultation* → remonte dans la veille ;
  - *notification sur une consultation où l'on est déjà engagé* → **e-mail « Actions à réaliser »**
    (ne remonte pas comme marché).
- **« Case à cocher » = étoile ⭐ Gmail** : une notif étoilée est « traitée » et ne revient plus ;
  sinon elle est **rappelée chaque semaine**. Lien direct vers l'e-mail d'origine dans chaque action.
- **Automatisation hebdo** : tâche Windows **`VeilleAO-Hebdo`** (lundi 08:00) → `veille-hebdo.bat`
  → `python -m src.main --no-open --email`. Installée par `installer-tache-hebdo.bat`.
- **Testé en réel** : Loyk a **reçu le 1er récap** ✅. Extraction validée sur un vrai e-mail achatpublic.

## 4. Réglages e-mail (déjà en place)
- Messagerie **Google Workspace** `adomsenior.fr` (MX `smtp.google.com`, DNS chez Cloudflare).
- IMAP `imap.gmail.com:993`, SMTP `smtp.gmail.com:587` (STARTTLS).
- Compte lu/expéditeur/destinataire : **`loyk.duporge@adomsenior.fr`**.
- **Mot de passe d'application** Google (2FA) → fichier local **`motdepasse-mail.txt`** (gitignoré,
  jamais commité). Lu aussi via variable d'env `VEILLE_SMTP_PASSWORD`. Espaces tolérés.
- **Filtre Gmail** créé : expéditeurs plateformes (`achatpublic.com`, `ternum-bfc.fr`, `maximilien.fr`,
  `marches-securises.fr`, `e-marchespublics.com`, `megalis.bretagne.bzh`, `marches-publics.gouv.fr`,
  `atexo.fr`) → **Archiver + Marquer comme lu + label `Notifications AO`**.

## 5. Points EN ATTENTE / à suivre ⏳
1. **Mise à jour du PC** : les dernières fonctions (⭐ case à cocher + lien vers l'e-mail) sont dans
   le code mais **pas encore sur le PC de Loyk** → il doit re-télécharger le ZIP de la branche,
   recréer `motdepasse-mail.txt`, relancer `installer-tache-hebdo.bat`.
2. **Google Workspace en fin d'essai gratuit** (~fin juillet 2026) → **doit être activé** sinon
   IMAP + envoi se coupent.
3. **PC allumé le lundi 8h** (ou cocher « Exécuter la tâche dès que possible après un démarrage
   manqué » dans le Planificateur → tâche `VeilleAO-Hebdo` → Paramètres).
4. **achatpublic n'a PAS d'alerte e-mail sur recherche sauvegardée** (seulement « Enregistrer ma
   recherche »). Les e-mails achatpublic reçus concernent des consultations déjà engagées. → pour les
   NOUVELLES opportunités achatpublic, relance la recherche à la main, OU compte sur BOAMP/TED.
5. **Créer des alertes de recherche sauvegardée** sur les plateformes qui, elles, poussent des e-mails
   (**Ternum BFC**, **maximilien**, **e-marchespublics**, **megalis**, **marches-sécurisés**) →
   règle d'or : **1 alerte = 1 mot-clé OU 1 code CPV** (jamais plusieurs mots ensemble = 0 résultat).
   Mots-clés & CPV recommandés dans `VEILLE-AUTOMATIQUE-HEBDO.md`.
6. **Flux RSS de plateformes** (section `plateformes.flux_rss` du `config.yaml`) : encore vide,
   optionnel — la voie e-mail (mail_alertes) la remplace avantageusement.

## 6. Fichiers clés
- `config.yaml` — sources, scoring (CPV lignes ~182-190, bailleurs, exclusions), section `email:`,
  section `mail_alertes:` (`dossier: "Notifications AO"`, `email_actions`, `actions_destinataire`).
- `src/main.py` — orchestration, `--email`, calcul nouveautés, envoi récap + rappel d'actions.
- `src/notify.py` — SMTP (`_smtp_send`), `send_recap`, `send_actions` (+ gabarits HTML), `_resolve_password`.
- `src/sources/mail_alertes.py` — lecture IMAP, classification opportunité/action, extraction,
  `_gmail_link`, `PENDING_ACTIONS`, détection étoile (`\Flagged`).
- `src/sources/plateformes.py` — lecteur RSS + regex partagées (`REF_RE`, `BUYER_RE`).
- `veille-hebdo.bat`, `installer-tache-hebdo.bat`, `desinstaller-tache-hebdo.bat`.
- `VEILLE-AUTOMATIQUE-HEBDO.md` — mode d'emploi complet (mdp appli, filtre, mots-clés/CPV, étoile).
- `PLATEFORMES-RSS.md`, `NOTE-REPONSE-MARCHE-AUXR_LOGIS-2026-48.md`.

## 7. Comment tester (sur le PC)
```
:: dans le dossier de l'outil (barre d'adresse -> cmd)
.venv\Scripts\python -m src.main --no-open --email
:: ou forcer la tâche :
schtasks /Run /TN "VeilleAO-Hebdo"
```
Chercher dans la sortie / `veille-hebdo.log` :
`alertes e-mail : X lus, Y consultation(s), Z action(s)...` puis `E-mail envoye a loyk.duporge@adomsenior.fr`.

## 8. Contraintes de l'environnement Claude (pour l'assistant)
- Le proxy **bloque les sites de marchés publics** (403) et le **DNS-over-HTTPS** → tester le scraping
  en direct est impossible ici ; le DNS brut UDP vers 1.1.1.1 marche (utilisé pour trouver le MX).
- Le connecteur **Gmail** de la session peut pointer vers `ets.ouhaddad@gmail.com` OU
  `loyk.duporge@adomsenior.fr` selon ce que Loyk a connecté — vérifier au début (les `toRecipients`).
- Ne JAMAIS demander / stocker le mot de passe d'application en clair dans le chat (déjà arrivé une
  fois → révoqué + recréé).

> Note volontairement limitée à **l'outil de veille marché** (les autres chantiers ADOMSENIOR ne sont
> pas couverts ici).
