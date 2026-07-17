# Activer toutes les plateformes (flux RSS) — mode d'emploi

## Pourquoi les flux RSS ?
Les plateformes de marchés publics (Ternum BFC, Maximilien, achatpublic, marchés-sécurisés,
e-marchespublics, Megalis, PLACE…) sont **rendues en JavaScript** et/ou **protégées** : elles
ne peuvent pas être « scrapées » directement, et **il n'existe aucune API commune**.

La seule méthode **fiable et durable** pour toutes les couvrir : s'abonner au **flux RSS** de
chaque **recherche sauvegardée**. L'outil lit ces flux, extrait les avis (titre, référence,
acheteur, date limite) et les **filtre + score automatiquement** comme le BOAMP.

> ⚠️ C'est ce qui aurait permis de capter le marché **AUXR_LOGIS 2026-48** (publié sur
> **Ternum BFC**, une plateforme non couverte jusqu'ici, et absent du BOAMP car procédure adaptée).

## La recette (identique sur toutes les plateformes)
1. **Crée un compte gratuit** sur la plateforme (obligatoire pour les alertes).
2. **Fais une recherche** avec tes mots-clés, par exemple :
   `adaptation PMR`, `remplacement baignoire douche`, `salle de bain`,
   `plomberie accessibilité`, `maintien à domicile` — et **ta zone** (région / départements).
3. **Enregistre la recherche** (bouton « M'alerter », « Enregistrer ma recherche »,
   « Créer une alerte »…) **et/ou clique sur l'icône RSS 🟧** des résultats.
4. **Copie l'URL du flux RSS** (clic droit sur l'icône RSS → « Copier le lien »).
5. Ouvre `config.yaml`, section `plateformes: > flux_rss:`, **décommente** la ligne de la
   plateforme et **remplace `COLLE_ICI`** par ton URL. Exemple :
   ```yaml
   plateformes:
     flux_rss:
       - { nom: "Ternum BFC (BFC)", url: "https://marches.ternum-bfc.fr/....rss" }
       - { nom: "Maximilien (IDF)", url: "https://www.maximilien.fr/....rss" }
   ```
6. **Relance `lancer`.** Les nouveaux marchés apparaissent dans le tableau.

## Où trouver le flux RSS, plateforme par plateforme

| Plateforme | Zone | Où cliquer |
|---|---|---|
| **Ternum BFC** (marches.ternum-bfc.fr) | Bourgogne-Franche-Comté | Compte → « Recherche avancée » → lancer la recherche → icône **RSS** en haut des résultats (ou « Créer une alerte »). |
| **Maximilien** (maximilien.fr) | Île-de-France | Compte → « Consultations » → rechercher → **« M'alerter »** / icône RSS. |
| **Megalis Bretagne** (megalis.bretagne.bzh) | Bretagne | Salle des marchés → recherche → icône **RSS**. |
| **PLACE** (marches-publics.gouv.fr) | État | Recherche avancée → **flux RSS** des résultats. |
| **achatpublic.com** | National | Compte → recherche → **« Enregistrer ma recherche »** → alerte (RSS/e-mail). |
| **marches-securises.fr** | National | Compte entreprise → recherche → **alerte RSS**. |
| **e-marchespublics.com** (Dematis) | National | Compte → recherche → **alerte** / RSS. |
| **marches-publics.info** (AWS) | National | Déjà couvert en direct (source `aws`) ; tu peux aussi ajouter son RSS. |

> 💡 Beaucoup de ces plateformes tournent sur le **même moteur (Atexo/MPE)** : le bouton RSS se
> trouve toujours au même endroit (en haut de la liste des consultations).

## Astuce : cible tes bailleurs
Sur chaque plateforme, tu peux aussi créer une alerte **par nom d'acheteur** (tes bailleurs
clients). Tu récupères alors TOUS leurs marchés, même hors mots-clés.

## Rappel important
- Les **données collectées** ne quittent pas ton PC ; seuls les flux publics sont lus.
- Fais tourner l'outil **depuis le disque local** (pas depuis un Drive synchronisé), sinon
  l'environnement Python peut se corrompre (voir README).
- Tu peux ajouter **autant de flux que tu veux** : autres régions, JAL, plateformes locales…
