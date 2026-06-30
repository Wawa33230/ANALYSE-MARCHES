# 🏢 Bailleurs clients — ciblage & analyse

Basé sur le fichier `Marches.csv` de l'ex-société apporteuse d'affaires : **109 marchés**,
**58 tiers** dont **~43 bailleurs** retenus comme **clients cibles** (les autres lignes
étaient des doublons, des particuliers — « MME MAILLARD » — ou des entités non bailleurs
— « GENDARMERIE », « OPH/SEM » génériques).

## Comment l'outil s'en sert

Ces bailleurs sont déclarés dans `config.yaml` sous **`bailleurs_cibles`**. Conséquences :

1. **Bonus fort + drapeau ★ client connu** : tout marché dont l'acheteur correspond à l'un
   d'eux remonte en haut du tableau de bord, signalé en doré.
2. **Recherche directe par nom** : BOAMP est interrogé **aussi par nom de bailleur**
   (sans filtre géographique), pour ne **jamais rater** un de leurs marchés, même si
   l'intitulé ne contient pas tes mots-clés habituels.

## Les bailleurs cibles (clients historiques)

13 Habitat · 3F Clairsienne · 3F Immobilière Rhône-Alpes · Orne Habitat · Aiguillon
Construction · Archipel Habitat · Aveyron Habitat · Brest Métropole Habitat · Corrèze
Habitat · Côte d'Azur Habitat · Creusalis · Domanys · Enéal · Erilia · Espacil Habitat ·
Est Ensemble Habitat · France Loire · Habitat Audois · Habitat HDF · Habitat Perpignan
Méditerranée · Hamaris · Haute-Savoie Habitat · In Cité · Ligéris · Lot Habitat · Manche
Habitat · Mésolia · Montluçon Habitat · Morbihan Habitat · Noalis · Nove Gestion · ODHAC ·
OPH de l'Ariège · Périgord Habitat · Polygone · SA HLM de l'Oise · Sèvre Loire Habitat ·
SIKOA · SIMAR · Un Toit Pour Tous · Val de Berry Habitat · Ozanam · OPH Agglo La Rochelle ·
Logiouest.

> Pour ajouter / retirer un bailleur : édite la liste `bailleurs_cibles` dans `config.yaml`.

## Calibrer les filtres à partir de leur historique 5 ans

⚠️ Ce n'est **pas** un second tableau de recherche. C'est un **outil d'analyse** dont le
but est d'**affiner les filtres** du tableau de bord, pour qu'il fasse remonter en
priorité les **vrais** marchés cibles.

Double-clique **`calibrer-filtres.bat`** (ou `python -m src.calibration`).
L'outil récupère **tous** les marchés de tes bailleurs sur 5 ans (sans filtre) et analyse :

- les **codes CPV** réellement utilisés sur leurs marchés salle de bain / plomberie ;
- le **vocabulaire réel** de leurs intitulés (mots et expressions les plus fréquents) ;
- les **types de marché** (accord-cadre, MAPA…) ;
- leur **niveau d'activité** par bailleur.

Il produit deux fichiers :
- `data/calibration-bailleurs.json` → **à m'envoyer** : je m'en sers pour régler les
  mots-clés et les CPV de `config.yaml` ;
- `output/calibration-bailleurs.txt` → un résumé lisible.

**Boucle d'amélioration :** tu lances `calibrer-filtres.bat` → tu m'envoies le `.json` →
j'ajuste les filtres → ton tableau de bord (`lancer.bat`) devient plus précis.

## Ce qu'on sait déjà de leurs critères (avant analyse)

Tirés du marché de référence (France Loire 2026020), valables pour la plupart des OPH/ESH :

- **Forme** : accord-cadre à bons de commande, souvent **multi-attributaires** (plusieurs
  titulaires retenus) → plusieurs entreprises peuvent gagner, c'est favorable à un nouvel
  entrant.
- **Critères de jugement** : **prix 40 % / valeur technique 60 %** → le **mémoire
  technique** est décisif (cf. `STRATEGIE-ET-FEUILLE-DE-ROUTE.md`).
- **Exigences récurrentes** : amiante **SS4** (patrimoine ancien), **décennale**,
  références 5 ans, CA 3 ans, **signature électronique qualifiée**.
- **Publication** : BOAMP + JOUE/TED pour les marchés formalisés, et **profil acheteur**
  (souvent **marches-publics.info / AWS**, parfois achatpublic.com, marches-securises.fr).
- **Lots géographiques** : ils découpent par secteur → tu peux ne candidater que sur les
  secteurs qui t'intéressent.
