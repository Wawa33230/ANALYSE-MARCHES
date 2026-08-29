# Veille automatique + récap par e-mail — mode d'emploi

L'outil tourne **tout seul** (tous les jours à 08h00 — recommandé pour ne rien
rater — ou chaque lundi, au choix à l'installation) et t'envoie **UN e-mail
récapitulatif unique** contenant :
- les **actions à réaliser** sur tes consultations en cours (en tête, en rouge),
- les consultations intéressantes, **nouveautés** surlignées,
- le **tableau de bord complet en pièce jointe** (fichier ZIP : double-clique
  dessus puis ouvre le fichier HTML qu'il contient).

Si le PC est **éteint ou en veille** à 08h00, la veille se lance automatiquement
**dès qu'il est rallumé** (rattrapage automatique installé avec la tâche).

En cas de doute (« le mail n'est pas arrivé », « la tâche a-t-elle tourné ? ») :
**double-clique sur `diagnostic.bat`** — il vérifie tout et envoie un mail de test.

Trois étapes, une seule fois. Compte ~5 minutes.

---

## Étape 1 — Créer un « mot de passe d'application » Gmail

> **Compte concerné : `loyk.duporge@adomsenior.fr`** (Google Workspace = même
> fonctionnement que Gmail : serveurs `smtp.gmail.com` / `imap.gmail.com`).
> Ce **même** mot de passe sert à la fois à **envoyer** le récap et à **lire** les
> alertes des plateformes.
>
> ⚠️ Google Workspace : si tu es **administrateur** du domaine, vérifie d'abord dans la
> console admin (admin.google.com) que **IMAP** et les **mots de passe d'application**
> sont autorisés (Sécurité → « Accès des applications moins sécurisées » / « IMAP »).

Gmail refuse d'envoyer via un programme avec ton mot de passe habituel. Il faut un
**mot de passe d'application** (16 caractères), spécifique à cet outil, révocable à tout moment.

1. Connecte-toi sur **loyk.duporge@adomsenior.fr**, puis active la **validation en 2 étapes** :
   → https://myaccount.google.com/security → « Validation en deux étapes » → activer.
2. Ensuite, va sur **https://myaccount.google.com/apppasswords**
3. Donne un nom (ex. `Veille AO`) → **Créer**.
4. Google affiche un code de **16 lettres** (ex. `abcd efgh ijkl mnop`). **Copie-le**
   (sans les espaces : `abcdefghijklmnop`).

> Ce mot de passe ne donne accès qu'à l'envoi de mail, pas à ton compte. Tu peux le
> supprimer quand tu veux depuis la même page.

---

## Étape 2 — Régler qui reçoit / qui envoie

Ouvre `config.yaml` (avec le Bloc-notes), section **`email:`** tout en bas :

```yaml
email:
  destinataire: "ets.ouhaddad@gmail.com"   # à QUI envoyer le récap
  expediteur:   "ets.ouhaddad@gmail.com"   # le compte Gmail qui envoie (celui de l'étape 1)
```

- `destinataire` = l'adresse où tu veux **recevoir** le récap (tu peux mettre une autre adresse).
- `expediteur` = le compte Gmail sur lequel tu as créé le mot de passe d'application.

(Le reste — `smtp_hote`, `smtp_port`, `securite` — est déjà bon pour Gmail, n'y touche pas.)

---

## Étape 3 — Installer la tâche hebdomadaire

**Double-clique sur `installer-tache-hebdo.bat`.**

- Il te demande de **coller le mot de passe d'application** de l'étape 1
  → il l'enregistre dans un fichier local `motdepasse-mail.txt` **qui reste sur ton PC**
  (il est exclu de GitHub, jamais envoyé nulle part).
- Puis il crée la tâche Windows **« VeilleAO-Hebdo »** qui se lancera **chaque lundi à 08h00**.

> Si Windows refuse (« Accès refusé »), fais **clic droit → Exécuter en tant
> qu'administrateur** sur `installer-tache-hebdo.bat`.

C'est fini. 🎉

---

## Tester tout de suite (sans attendre le prochain créneau)

- **Le plus simple : double-clique sur `diagnostic.bat`.** Il vérifie la tâche
  planifiée, le mot de passe, la lecture Gmail (IMAP), l'envoi (SMTP), et
  t'envoie un **e-mail de test**. Chaque point affiche `[OK]` ou `[ERREUR]` avec le remède.

- **Lancer une vraie collecte + envoi** — dans le dossier, tape `cmd` dans la barre d'adresse puis :
  ```
  schtasks /Run /TN "VeilleAO-Hebdo"
  ```
  (ou double-clique sur `veille-hebdo.bat`). Le résultat s'écrit dans `veille-hebdo.log`.

- **Où vérifier ce qui s'est passé** :
  - `data\derniere-execution.txt` — date/heure et résultat de la dernière exécution ;
  - `data\journal-envois.log` — chaque e-mail : ENVOYÉ ou ÉCHEC + la raison ;
  - `veille-hebdo.log` — le détail complet des exécutions automatiques.

---

## Mettre à jour l'outil

**Double-clique sur `mettre-a-jour.bat`** : il télécharge la dernière version,
remplace les fichiers **en conservant** ton mot de passe (`motdepasse-mail.txt`),
ton historique (`data\`, `output\`) et en sauvegardant ton ancien `config.yaml`
(copie `config-precedente.yaml`), puis **re-pointe la tâche planifiée** vers le
dossier. Plus besoin de re-télécharger le ZIP ni de réinstaller quoi que ce soit.

---

## Changer le jour / l'heure

- **Le plus simple** : ouvre le **Planificateur de tâches** Windows (menu Démarrer →
  « Planificateur de tâches ») → dossier **Bibliothèque** → tâche **VeilleAO-Hebdo** →
  onglet **Déclencheurs** → modifier.
- Ou réinstalle avec une autre planification. Exemples (invite de commande dans le dossier) :
  ```
  rem  Tous les lundis à 7h30
  schtasks /Create /F /TN "VeilleAO-Hebdo" /SC WEEKLY /D MON /ST 07:30 /TR "\"%CD%\veille-hebdo.bat\""
  rem  Tous les jours à 8h
  schtasks /Create /F /TN "VeilleAO-Hebdo" /SC DAILY /ST 08:00 /TR "\"%CD%\veille-hebdo.bat\""
  ```

## Désinstaller

Double-clique sur **`desinstaller-tache-hebdo.bat`** (tes fichiers et ton mot de passe
restent en place ; seule la planification est retirée).

---

## Réglages fins (facultatif) — section `email:` du `config.yaml`

| Réglage | Rôle |
|---|---|
| `envoyer_recap: true` | envoyer un mail à **chaque** lancement (même manuel), pas seulement la tâche automatique |
| `joindre_tableau: false` | ne pas joindre le tableau de bord (joint en **ZIP** : un `.html` brut est parfois bloqué par Gmail) |
| `envoyer_si_vide: false` | ne **pas** envoyer de mail quand il n'y a aucune cible ni action |
| `email_unique: false` | revenir à **deux** e-mails séparés (récap + actions) — déconseillé |
| `objet_prefixe: "..."` | changer le début de l'objet du mail |

---

# Alertes plateformes (Ternum BFC, achatpublic, maximilien…)

La plupart des plateformes **n'ont plus de flux RSS** : elles envoient des **alertes
e-mail** sur recherche sauvegardée. L'outil **lit ces alertes dans ta boîte Gmail**
(en lecture seule, avec le **même mot de passe d'application** que l'envoi) et en
extrait les consultations, filtrées et scorées comme le reste.

## Faut-il une adresse e-mail dédiée ? — NON

Les plateformes envoient l'alerte à **l'adresse de ton compte** (tu ne choisis pas).
Inutile d'en créer une exprès :
- Garde ton adresse habituelle (ex. `ets.ouhaddad@gmail.com`).
- L'outil ne lit **que** les e-mails venant des plateformes (liste `expediteurs` du
  `config.yaml`) : tes autres mails ne sont pas touchés.

**Recommandé (plus propre) — un libellé Gmail dédié :**
1. Gmail → roue crantée → **Voir tous les paramètres** → **Filtres** → **Créer un filtre**.
2. Champ « De » : `ternum-bfc.fr OR achatpublic.com OR maximilien.fr OR marches-securises.fr OR e-marchespublics.com OR megalis.bretagne.bzh OR marches-publics.gouv.fr` → **Créer un filtre**.
3. Coche **Appliquer le libellé** → **Nouveau libellé** : `Notifications AO` → **Créer le filtre**.
4. Dans `config.yaml`, section `mail_alertes:`, mets `dossier: "Notifications AO"` (déjà fait).

> 💡 Quand l'outil lit un **libellé dédié**, il prend en compte **tous** les e-mails
> qui s'y trouvent, quel que soit l'expéditeur : pour **ajouter une plateforme**, il
> suffit d'ajouter son domaine au **filtre Gmail** — rien à changer dans l'outil.

(Sans libellé, laisse `dossier: "INBOX"` : l'outil filtre alors par expéditeur,
liste `expediteurs` du `config.yaml`.)

## Format de l'alerte : HTML ou texte ?

Choisis **HTML** si la plateforme te laisse le choix (extraction plus fiable des
titres et des liens). Le lecteur gère aussi le format texte, mais l'HTML est meilleur.

## ⚠️ La règle d'or : des alertes LARGES

Ne mets **jamais** plusieurs mots-clés dans le même champ (ex.
`salle de bain adaptation PMR remplacement baignoire douche`) : la plupart des moteurs
les combinent en **ET** → **0 résultat** (c'est ce qui t'était arrivé). À la place :
crée **plusieurs alertes séparées**, chacune avec **UN seul mot-clé** ou **UN seul code
CPV**. On ratisse large côté plateforme ; c'est **l'outil qui trie et score** ensuite.

### Mots-clés — une alerte par ligne
| Alerte | Mot-clé à saisir |
|---|---|
| 1 | `adaptation PMR` |
| 2 | `remplacement baignoire` |
| 3 | `baignoire douche` |
| 4 | `salle de bain` |
| 5 | `salle d'eau` |
| 6 | `accessibilité` |
| 7 | `maintien à domicile` |
| 8 | `douche` |
| 9 | `receveur` |
| 10 | `panneaux muraux` |

### Codes CPV — une alerte par code (si le site propose la recherche par CPV)
| Code CPV | Intitulé | Priorité |
|---|---|---|
| `45332400` | Travaux d'installation d'appareils sanitaires | ⭐⭐⭐ |
| `45330000` | Travaux de plomberie | ⭐⭐⭐ |
| `45332000` | Plomberie + pose de conduits d'évacuation | ⭐⭐ |
| `45211310` | Salles de bains | ⭐⭐ |
| `44411000` | Articles sanitaires (baignoires, douches, receveurs) | ⭐⭐ |
| `45454100` | Travaux de rénovation | ⭐ |

> 💡 Tu peux aussi créer des alertes **par nom de bailleur** (tes clients : France Loire,
> Logiouest, Creusalis…) : tu récupères alors **tous** leurs marchés, même hors mots-clés.

## Deux types d'e-mails, deux traitements

L'outil distingue automatiquement :

1. **Nouvelle opportunité** (alerte « nouvelle consultation qui correspond à ta recherche »)
   → **remonte dans la veille** (tableau de bord + récap hebdo), filtrée et scorée.
2. **Notification sur une consultation où tu es DÉJÀ engagé** (demande de complément,
   question/réponse, changement de date limite, document à retirer…)
   → **ne remonte PAS** comme nouveau marché. À la place, tu reçois un e-mail
   **« Actions à réaliser »** sur ta boîte principale, avec la nature de l'action,
   la consultation, l'échéance et **deux liens** : « Ouvrir l'e-mail » (vers le mail
   d'origine dans Gmail) et « Voir la consultation ».

### La « case à cocher » = l'étoile ⭐ Gmail
L'e-mail « Actions à réaliser » est un **rappel hebdomadaire des actions non traitées** :
- tant qu'une action n'est **pas faite**, elle **revient** dans le rappel chaque semaine ;
- quand tu l'as traitée, ouvre l'e-mail d'origine (bouton du rappel) et clique sur
  l'**étoile ⭐** dans Gmail → l'outil la considère **traitée** et **ne la remet plus**.

C'est une case à cocher « native » : aucune manip technique, juste l'étoile Gmail.
(Astuce : les actions ne sont lues que sur les `jours_recents` derniers jours ; une
notification non étoilée cesse d'être rappelée passé cette fenêtre.)

Réglages (`config.yaml`, section `mail_alertes:`) :
| Réglage | Rôle |
|---|---|
| `email_actions: true` | activer l'e-mail « Actions à réaliser » (mets `false` pour le couper) |
| `actions_destinataire: ""` | destinataire de l'e-mail d'actions (vide = même que le récap) |

## Activer côté outil
Dans `config.yaml` : `sources: > mail_alertes: true` (déjà activé par défaut) et vérifie
la section `mail_alertes:` (compte, dossier). Le mot de passe est le **même** que pour
l'envoi (rien de plus à faire si tu as suivi les étapes 1 à 3).

---

## Points importants

- **PC éteint à 08h00 ?** Pas grave : l'installateur active désormais le **rattrapage
  automatique** (« Exécuter dès que possible après un démarrage manqué ») + la **sortie
  de veille**. Si la tâche a été installée avec une ancienne version, relance simplement
  `installer-tache-hebdo.bat` une fois.
- Le mot de passe d'application vit **uniquement** dans `motdepasse-mail.txt` sur ton PC
  (ou dans la variable d'environnement `VEILLE_SMTP_PASSWORD`). Il n'est **jamais** publié
  sur GitHub.
- Fais tourner l'outil **depuis le disque local** (pas depuis un Drive synchronisé), sinon
  l'environnement Python peut se corrompre.
- « Nouveautés » = marchés absents de la **collecte précédente**. La comparaison se fait sur
  les fichiers `data/marches-*.json` ; ne les supprime pas si tu veux garder l'historique.
