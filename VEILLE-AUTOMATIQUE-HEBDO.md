# Veille automatique 1×/semaine + récap par e-mail — mode d'emploi

L'outil peut tourner **tout seul une fois par semaine** (lundi 08h00 par défaut) et
t'envoyer un **e-mail récapitulatif** des consultations intéressantes, avec les
**nouveautés** de la semaine surlignées et le **tableau de bord complet en pièce jointe**.

Trois étapes, une seule fois. Compte ~5 minutes.

---

## Étape 1 — Créer un « mot de passe d'application » Gmail

Gmail refuse d'envoyer via un programme avec ton mot de passe habituel. Il faut un
**mot de passe d'application** (16 caractères), spécifique à cet outil, révocable à tout moment.

1. Le compte qui **envoie** le mail doit avoir la **validation en 2 étapes activée** :
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

## Tester tout de suite (sans attendre lundi)

Deux options :

- **Le mail seulement** — dans le dossier, tape dans la barre d'adresse `cmd` puis :
  ```
  schtasks /Run /TN "VeilleAO-Hebdo"
  ```
  (ou double-clique sur `veille-hebdo.bat`). Le résultat s'écrit dans `veille-hebdo.log`.

- **Vérifier l'envoi e-mail en direct** : ouvre une invite de commande dans le dossier et lance :
  ```
  .venv\Scripts\python -m src.main --no-open --email
  ```
  Les messages t'indiquent si le mail est **parti** ou **pourquoi** il ne part pas.

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
| `envoyer_recap: true` | envoyer un mail à **chaque** lancement (même manuel), pas seulement la tâche hebdo |
| `joindre_tableau: false` | ne pas joindre le tableau de bord HTML |
| `envoyer_si_vide: false` | ne **pas** envoyer de mail les semaines sans aucune cible |
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
3. Coche **Appliquer le libellé** → **Nouveau libellé** : `Alertes-AO` → **Créer le filtre**.
4. Dans `config.yaml`, section `mail_alertes:`, mets `dossier: "Alertes-AO"`.

(Sans ça, laisse `dossier: "INBOX"` : l'outil filtre quand même par expéditeur.)

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

## Activer côté outil
Dans `config.yaml` : `sources: > mail_alertes: true` (déjà activé par défaut) et vérifie
la section `mail_alertes:` (compte, dossier). Le mot de passe est le **même** que pour
l'envoi (rien de plus à faire si tu as suivi les étapes 1 à 3).

---

## Points importants

- **L'ordinateur doit être allumé** à l'heure prévue (le Planificateur peut rattraper un
  créneau manqué : coche « Exécuter dès que possible après un démarrage manqué » dans les
  propriétés de la tâche).
- Le mot de passe d'application vit **uniquement** dans `motdepasse-mail.txt` sur ton PC
  (ou dans la variable d'environnement `VEILLE_SMTP_PASSWORD`). Il n'est **jamais** publié
  sur GitHub.
- Fais tourner l'outil **depuis le disque local** (pas depuis un Drive synchronisé), sinon
  l'environnement Python peut se corrompre.
- « Nouveautés » = marchés absents de la **collecte précédente**. La comparaison se fait sur
  les fichiers `data/marches-*.json` ; ne les supprime pas si tu veux garder l'historique.
