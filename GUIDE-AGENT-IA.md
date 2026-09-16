# Guide — Agent IA de reclassement des marchés

> L'agent IA relit **chaque marché** trouvé par l'outil et attribue sa **propre note
> de pertinence** (jugement métier, pas juste des mots-clés), avec une **raison en
> une phrase**. Il corrige les deux défauts du score par mots-clés : les marchés
> parfaits qui plafonnaient à ~75, et le bruit (collectivités hors sujet qui
> remontaient juste parce qu'elles contenaient « PMR » ou « accessibilité »).

---

## 1. Ce que ça change concrètement

| Avant (mots-clés seuls) | Après (agent IA) |
|---|---|
| Un marché 100 % cible plafonne à ~75 | Il monte à ~90-100 et passe en tête |
| Une mairie « rampe d'accès école » remonte à 40 (bruit) | L'IA comprend que ce n'est **pas du logement adapté** → note ~10 → disparaît |
| Aucune explication | Une phrase : *« Adaptation SDB PMR pour un bailleur = cœur de cible »* |

L'IA **fait autorité** : elle remplace le score et la catégorie. Le score par
mots-clés reste affiché (dans le détail du marché) pour transparence.

---

## 2. Activation en 4 étapes

### Étape 1 — Créer une clé API Claude
1. Va sur **console.anthropic.com** (crée un compte si besoin — c'est séparé de
   claude.ai).
2. Menu **API Keys** → **Create Key** → copie la clé (commence par `sk-ant-...`).
3. Ajoute un petit crédit (menu **Billing**) : **5 € suffisent pour des mois**
   (voir coût plus bas).

### Étape 2 — Ranger la clé (sans jamais la mettre dans un fichier versionné)
Dans le dossier de l'outil, crée un fichier **`cle-ia.txt`** contenant **uniquement
la clé**, sur une seule ligne. (Comme `motdepasse-mail.txt`, il est ignoré par git.)

> Bloc-notes : `notepad cle-ia.txt` → colle la clé → Enregistrer.

*(Alternative : variable d'environnement `VEILLE_IA_KEY`.)*

### Étape 3 — Activer l'agent dans `config.yaml`
Cherche la section `ia:` et passe :
```yaml
ia:
  actif: true            # <-- passe de false a true
  modele: "claude-haiku-4-5"
```

### Étape 4 — Installer la librairie (une seule fois)
```
pip install anthropic
```
*(ou double-clic sur `mettre-a-jour.bat` puis relance — `anthropic` est dans
`requirements.txt`.)*

C'est tout. Au prochain lancement, tu verras dans la console :
```
>> Agent IA (claude-haiku-4-5) : 37 marche(s) a analyser (0 depuis le cache).
   37 marche(s) reclasse(s) par l'agent IA.
```
Et dans le tableau / l'e-mail, chaque marché porte une note IA + sa raison 🤖.

---

## 3. Coût (rassurant)

- Modèle par défaut **Claude Haiku** = le moins cher.
- On envoie les marchés **par lots** et on **met en cache** chaque verdict
  (`data/ia-cache.json`) : **un marché déjà noté n'est jamais renoté**.
- En régime quotidien, seuls les **nouveaux** marchés sont analysés (quelques
  dizaines/jour) → de l'ordre de **quelques centimes par mois**.

Si un jour tu veux un jugement encore plus fin (au prix d'un coût plus élevé),
change une ligne :
```yaml
  modele: "claude-sonnet-5"   # ou "claude-opus-5"
```

---

## 4. Réglages (section `ia:` de `config.yaml`)

| Réglage | Rôle |
|---|---|
| `actif` | `true`/`false` — active l'agent |
| `modele` | `claude-haiku-4-5` (défaut) / `claude-sonnet-5` / `claude-opus-5` |
| `taille_lot` | nb de marchés par appel (défaut 12) |
| `cle_env` | variable d'environnement de la clé (défaut `VEILLE_IA_KEY`) |
| `cle_fichier` | fichier local de la clé (défaut `cle-ia.txt`) |
| `cache_fichier` | mémoire des verdicts (défaut `data/ia-cache.json`) |
| `definition_cible` | (avancé) redéfinir la description du métier cible |

**Affiner le jugement de l'IA** : la définition de la cible (ce qui est « cible »
vs « hors cible ») est dans `src/tri_ia.py` (`DEFINITION_CIBLE`). Tu peux la
surcharger sans toucher au code via `ia.definition_cible` dans le config. Après
un changement de définition, supprime `data/ia-cache.json` pour forcer une
renotation complète.

---

## 5. Sécurité & robustesse

- La clé API n'est **jamais** dans un fichier versionné (`cle-ia.txt` est
  gitignoré, exactement comme le mot de passe mail). Ne la colle **jamais** dans
  une conversation.
- Si la clé manque, si tu es hors-ligne, ou en cas d'erreur API : l'outil
  **continue** avec le score par mots-clés (aucun plantage, aucun marché perdu).
