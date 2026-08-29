# Intégrer TOUTES les plateformes — plan de couverture complet

> Objectif : **ne rater aucun marché** « remplacement baignoire → douche / PMR /
> salle de bain » publié en France, comme le ferait un service payant type
> DoubleTrade / Vecteur Plus — mais gratuitement.

## Comment l'outil couvre le marché (3 canaux)

| Canal | Ce que ça couvre | Ce que tu as à faire |
|---|---|---|
| **1. BOAMP + TED (API, automatique)** | Toutes les annonces **légalement publiées** au niveau national (BOAMP) et européen (TED). La grande majorité des marchés > 90 k€ y passent. | **Rien** — déjà actif. |
| **2. Alertes e-mail des plateformes** | Les marchés < 90 k€ (MAPA) publiés **seulement** sur le profil d'acheteur de la plateforme. | Créer **une fois** des alertes de recherche sur chaque plateforme (tableau ci-dessous). L'outil lit les e-mails automatiquement. |
| **3. Scraper / RSS** | e-marchespublics en direct ; toute plateforme offrant un flux RSS. | Coller l'URL RSS dans `config.yaml` si une plateforme en propose un. |

**Le canal n°2 est la clé** : c'est le moyen universel, fiable et durable de couvrir
n'importe quelle plateforme. Une alerte créée = des marchés qui arrivent tout seuls.

## Le principe (une seule fois par plateforme)

1. **Crée un compte gratuit** entreprise sur la plateforme.
2. Fais une **recherche** puis **enregistre-la en alerte e-mail** — règle d'or :
   **1 alerte = 1 mot-clé** (ou 1 code CPV). Jamais plusieurs mots ensemble.
   Mots-clés conseillés : `salle de bain` · `douche` · `baignoire` · `accessibilité` ·
   `adaptation PMR` · `maintien à domicile` · `receveur` · `panneaux muraux`
   CPV conseillés : `45332400` · `45330000` · `45211310` · `44411000`
3. **Ajoute le domaine d'envoi au filtre Gmail** « Notifications AO »
   (Gmail → Paramètres → Filtres → modifier le filtre → ajouter `OR domaine.fr` dans « De »).
4. C'est tout : l'outil lit le libellé « Notifications AO » et intègre **tous** les
   e-mails qui s'y trouvent, quel que soit l'expéditeur.

## Les plateformes, par ordre de priorité

| ✔ | Plateforme | Couverture | Alerte e-mail ? | Domaine d'envoi (filtre Gmail) |
|---|---|---|---|---|
| ☐ | **marches-publics.info (AWS)** | ~50 % des MAPA de France | Oui (« Mes recherches / alertes ») | `marches-publics.info`, `aws-achat.info`, `agysoft.fr` |
| ☐ | **e-marchespublics (Dematis)** | Nationale, très utilisé bailleurs | Oui | `e-marchespublics.com`, `dematis.com` |
| ☐ | **PLACE / marches-publics.gouv.fr** | État + nombreux OPH | Oui (recherche sauvegardée) | `marches-publics.gouv.fr`, `atexo` |
| ☐ | **Maximilien** | Île-de-France (bailleurs franciliens ++) | Oui | `maximilien.fr` |
| ☐ | **marches-securises.fr** | Nationale | Oui | `marches-securises.fr` |
| ☐ | **BOAMP alertes** | Redondant avec l'API mais gratuit, sûr | Oui | `boamp.fr` |
| ☐ | **Ternum BFC** | Bourgogne-Franche-Comté | Oui | `ternum-bfc.fr` |
| ☐ | **Megalis Bretagne** | Bretagne | Oui | `megalis.bretagne.bzh` |
| ☐ | **Klekoon** | Nationale | Oui | `klekoon.com` |
| ☐ | **France Marchés** | Agrégateur des journaux (JAL) | Oui | `francemarches.com` |
| ☐ | **MarchesOnline (Moniteur)** | Nationale BTP | Oui | `marchesonline.com` |
| ☐ | **Centrale des marchés** | Agrégateur | Oui | `centraledesmarches.com` |
| ☐ | **Achat Solutions / MPS** | Sud + collectivités | Oui | `achatsolutions.fr` |
| ☐ | **achatpublic.com** | Nationale, gros bailleurs | ⚠️ **Non** pour les nouveautés (confirmé par leur support) : seulement des notifications de suivi. Relance ta recherche à la main de temps en temps ; les nouveautés passent en général aussi par BOAMP. | `achatpublic.com` (déjà dans le filtre) |

Coche au fur et à mesure. **Les 5 premières lignes couvrent l'essentiel du volume national.**

> Tous les domaines ci-dessus sont déjà connus de l'outil (jolis libellés + liste
> `expediteurs` de `config.yaml`). Si tu utilises une plateforme absente du tableau,
> ajoute simplement son domaine au filtre Gmail : le libellé étant lu en entier,
> elle sera intégrée automatiquement.

## Alertes « par bailleur » (recommandé en plus)

Sur AWS et e-marchespublics, crée aussi des alertes **par nom d'acheteur** pour tes
bailleurs clients (France Loire, Logiouest, Creusalis, Clairsienne…) : tu reçois alors
**tous** leurs marchés, même mal libellés — c'est exactement ce que font les outils payants.

## Vérifier que ça marche

Après avoir créé une alerte, attends le premier e-mail de la plateforme puis
double-clique sur `diagnostic.bat` : la ligne IMAP indique combien d'e-mails
récents sont vus dans « Notifications AO ». Ils apparaîtront dans le prochain récap.
