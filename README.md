# 🛁 Veille Appels d'Offres — Salle de bain / Accessibilité PMR

Outil **local** (sur ton PC) qui récupère automatiquement les appels d'offres publics
correspondant à ton métier — **remplacement de baignoire par douche, adaptation PMR,
pose de panneaux muraux** pour bailleurs sociaux — et les présente dans un tableau de
bord clair, **classé par pertinence**, avec les dates limites et les liens directs.

Il a été calibré à partir d'un vrai marché cible (**France Loire — réf. 2026020**,
lot 01 Plomberie / Travaux d'Accessibilité).

---

## 🚀 Démarrage (Windows)

### Étape 0 — Récupérer le projet sur ton PC (indispensable)
Les fichiers doivent être **sur ton ordinateur** pour fonctionner et pour s'ouvrir dans
le Bloc-notes (sur GitHub dans le navigateur, ils ne sont pas encore chez toi).
1. Sur la page GitHub, vérifie que la **branche** affichée est bien
   `claude/tender-search-tool-setup-x65gpm`.
2. Bouton vert **`< > Code`** → **`Download ZIP`**.
3. Dans **Téléchargements**, **clic droit** sur le ZIP → **« Extraire tout… »**
   (par ex. sur le Bureau).
4. Travaille toujours **depuis le dossier extrait** — jamais depuis le ZIP ni le navigateur.

### Étape 1 — Installer Python (une seule fois)
1. Va sur **https://www.python.org/downloads/** et télécharge Python 3.
2. Lance l'installateur et **COCHE bien la case « Add Python to PATH »** (en bas de la
   première fenêtre), puis « Install Now ».

### Étape 2 — Voir tout de suite à quoi ça ressemble (mode démo)
- Double-clique sur **`apercu-demo.bat`**.
- Une page web s'ouvre dans ton navigateur avec des marchés **fictifs** d'exemple.
- C'est exactement le rendu que tu auras avec les vrais marchés.

### Étape 3 — Lancer la vraie recherche
- Double-clique sur **`lancer.bat`**.
- La première fois, l'outil installe ses composants (1 à 2 minutes).
- Il interroge les sources, puis ouvre le tableau de bord avec les **vrais** appels
  d'offres en cours.

> 💡 Refais l'étape 3 quand tu veux : idéalement **2 fois par semaine** (lundi / jeudi)
> pour ne rien rater. Chaque lancement régénère le tableau à jour.

---

## 📊 Lire le tableau de bord

| Élément | Signification |
|---|---|
| **Score (0-100)** | Pertinence par rapport à ton métier. 🟢 ≥55 = cible prioritaire, 🟡 ≥28 = à regarder. |
| **Jours** | Jours restants avant la date limite. 🔴 rouge = moins de 7 jours (urgent !). |
| **Tags** | `bailleur social`, `accord-cadre`, `amiante (SS4)`, `carrelage/faience`, `autres lots…` |
| **Clic sur l'objet** | Déplie le détail : mots-clés détectés, CPV, description. |
| **Ouvrir ↗** | Lien direct vers l'avis officiel (à lire **avant** toute décision). |

**Boutons de filtre :** Tous / Prioritaires / À regarder / Cette semaine (<7j).
**Recherche :** tape un mot (acheteur, département, mot-clé) pour filtrer instantanément.
**Tri :** clique sur un en-tête de colonne (Score, Limite, Dpt…) pour trier.

> ⚠️ Le tag **`carrelage/faience`** signale un marché orienté carrelage. Tu poses des
> panneaux muraux : ces marchés sont **rétrogradés** mais pas supprimés (tu peux parfois
> proposer une variante panneau). À toi de juger au cas par cas.

---

## ⚙️ Personnaliser la recherche — `config.yaml`

Ouvre **`config.yaml`** avec le Bloc-notes. Tout est commenté en français. Tu peux :

- **Restreindre la zone géographique** :
  ```yaml
  geographie:
    perimetre: departements
    departements: ["45", "18", "44", "49", "85"]
  ```
- **Élargir / réduire la période** : `jours_recents: 45`
- **Ajouter un mot-clé cible** (ex. un produit que tu poses) dans `mots_cles_prioritaires`.
- **Ajouter une exclusion** (ex. un type de marché qui ne t'intéresse pas) dans `mots_cles_exclus`.
- **Régler la sévérité** via `seuil_prioritaire` / `seuil_a_regarder`.
- **Afficher aussi les hors-cible** : `garder_hors_cible: true`.

Après modification, relance `lancer.bat`.

---

## 🔗 Ajouter les plateformes (marches-publics.info, etc.)

Les plateformes de dématérialisation n'ont pas d'API publique fiable. La méthode
**durable** consiste à utiliser leurs **flux RSS d'alerte** :

1. Crée un compte gratuit sur **marches-publics.info** (c'est là que publie France Loire).
2. Fais une recherche : `plomberie accessibilité`, `adaptation salle de bain`, `PMR`, etc.
3. **Enregistre la recherche en alerte** et récupère l'URL de son **flux RSS**.
4. Colle cette URL dans `config.yaml` :
   ```yaml
   plateformes:
     flux_rss:
       - "https://www.marches-publics.info/.../mon-alerte.rss"
   ```
5. Relance `lancer.bat` : les annonces de la plateforme s'ajoutent au tableau.

Tu peux ajouter autant de flux que tu veux (achatpublic.com, marches-securises.fr…).

> 📌 Bonne nouvelle : la **plupart des accords-cadres formalisés** de bailleurs (comme
> France Loire) sont **déjà** publiés sur BOAMP et TED, donc captés sans configuration.
> Les flux servent surtout pour les marchés en procédure adaptée (MAPA), plus petits.

---

## 🧠 Comment l'outil décide (logique de score)

Pour chaque annonce, le moteur additionne :
- des **points** si l'objet contient tes mots-clés (baignoire, douche, accessibilité, PMR…) ;
- des **points** pour les codes CPV plomberie/sanitaire (45330000, 45332400, 45211310…) ;
- un **bonus** si l'acheteur est un bailleur social, et si c'est un accord-cadre.

Puis il **écarte** les marchés de « grosse plomberie » (chauffage, chaudière, VMC, gaz…)
**sauf** s'ils contiennent un vrai signal salle de bain — un marché multi-lots du type
*« électricité, plomberie, menuiseries »* (cas France Loire) reste donc bien détecté.

---

## 📁 Structure du projet

```
ANALYSE-MARCHES/
├── lancer.bat              ← double-clic : lance la vraie recherche
├── apercu-demo.bat        ← double-clic : aperçu avec données fictives
├── config.yaml            ← tous tes réglages (mots-clés, zone, seuils)
├── requirements.txt
├── src/
│   ├── main.py            ← orchestrateur
│   ├── scoring.py         ← moteur de pertinence
│   ├── dashboard.py       ← génération du tableau HTML
│   └── sources/           ← connecteurs BOAMP / TED / plateformes
├── data/                  ← historique des collectes (1 fichier .json par jour)
└── output/                ← le tableau de bord généré (.html)
```

---

## ❓ Problèmes courants

- **« Python n'a pas été trouvé » / la fenêtre se ferme ou rien ne s'actualise** →
  ouvre l'Invite de commandes (`cmd`) et tape `python --version`.
  - Si ça ouvre le **Microsoft Store** ou dit « n'est pas reconnu » : Python n'est pas
    dans le PATH. **Réinstalle** depuis python.org en cochant **« Add python.exe to PATH »**,
    puis **redémarre l'ordinateur**.
  - Le lanceur garde maintenant la fenêtre noire ouverte (`pause`) : lis le message
    affiché, il indique précisément quoi corriger.
- **« requirements.txt introuvable »** → tu n'as pas le projet complet : refais l'**Étape 0**
  (Download ZIP + Extraire tout) et lance le `.bat` depuis le dossier extrait.
- **Une source affiche « indisponible »** → ce n'est pas bloquant, l'outil continue avec
  les autres. Réessaie plus tard (le site public était peut-être momentanément lent).
- **Le tableau est vide** → élargis `jours_recents`, ou passe `perimetre: national`,
  ou baisse `seuil_a_regarder`.

---

📄 Voir aussi **`STRATEGIE-ET-FEUILLE-DE-ROUTE.md`** : l'analyse du projet global et le
plan pour passer de sous-traitant à **titulaire direct** des marchés.
