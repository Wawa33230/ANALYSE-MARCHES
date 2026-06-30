"""Point d'entree de l'outil de veille.

Usage :
    python -m src.main             # collecte en ligne (BOAMP + TED + plateformes)
    python -m src.main --demo      # mode demonstration (donnees fictives, sans reseau)
    python -m src.main --no-open   # ne pas ouvrir le navigateur automatiquement
    python -m src.main --config autre.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from datetime import date

from .config import Config
from .scoring import score_tender, _parse_date
from .dashboard import render
from . import sample_data


def _dedupe(tenders: list) -> list:
    """Supprime les doublons (meme id, ou meme objet+acheteur)."""
    seen_id, seen_key, out = set(), set(), []
    for t in tenders:
        from .scoring import normalize, as_text
        key = normalize(as_text(t.title)[:80] + "|" + as_text(t.buyer))
        if t.id in seen_id or key in seen_key:
            continue
        seen_id.add(t.id)
        seen_key.add(key)
        out.append(t)
    return out


def collect(config: Config, demo: bool) -> list:
    if demo:
        print(">> Mode DEMONSTRATION (donnees fictives, aucune connexion).")
        return sample_data.fetch_demo()

    tenders = []
    sources = config.sources

    if sources.get("boamp"):
        tenders += _run_source("BOAMP", config)
    if sources.get("ted"):
        tenders += _run_source("TED", config)
    if sources.get("aws"):
        tenders += _run_source("AWS", config)
    if sources.get("plateformes"):
        tenders += _run_source("plateformes", config)

    return tenders


def _run_source(name: str, config: Config) -> list:
    print(f">> Source {name} ...")
    try:
        if name == "BOAMP":
            from .sources import boamp as mod
        elif name == "TED":
            from .sources import ted as mod
        elif name == "AWS":
            from .sources import marches_publics_info as mod
        else:
            from .sources import plateformes as mod
        result = mod.fetch(config)
        print(f"   {len(result)} avis recuperes.")
        return result
    except Exception as e:  # noqa: BLE001
        print(f"   /!\\ Source {name} indisponible : {e}")
        print(f"       (l'outil continue avec les autres sources)")
        return []


def main(argv=None):
    parser = argparse.ArgumentParser(description="Veille appels d'offres - salle de bain / accessibilite")
    parser.add_argument("--demo", action="store_true", help="Donnees de demonstration (sans reseau)")
    parser.add_argument("--no-open", action="store_true", help="Ne pas ouvrir le navigateur")
    parser.add_argument("--config", default=None, help="Chemin d'un config.yaml alternatif")
    args = parser.parse_args(argv)

    config = Config.load(args.config)
    scoring_cfg = config.scoring

    print("=" * 64)
    print(" VEILLE APPELS D'OFFRES - Remplacement baignoire/douche & PMR")
    print("=" * 64)

    tenders = collect(config, args.demo)
    tenders = _dedupe(tenders)

    # Scoring
    for t in tenders:
        score_tender(t, scoring_cfg)

    # Filtrage : marches echus
    if config.get("recherche.masquer_echus", True):
        before = len(tenders)
        tenders = [t for t in tenders if _keep_not_expired(t)]
        if before - len(tenders):
            print(f">> {before - len(tenders)} marche(s) echu(s) masque(s).")

    # Filtrage : hors cible
    if not config.get("affichage.garder_hors_cible", False):
        tenders = [t for t in tenders if t.category != "hors_cible"]

    prio = sum(1 for t in tenders if t.category == "prioritaire")
    print(f">> {len(tenders)} marche(s) retenu(s) dont {prio} prioritaire(s).")

    # Sauvegarde brute (cache / historique)
    _save_json(tenders)

    # Tableau de bord
    out = config.get("affichage.fichier_sortie", "output/tableau-de-bord.html")
    path = render(tenders, out)
    print(f">> Tableau de bord genere : {os.path.abspath(path)}")

    if config.get("affichage.ouvrir_navigateur", True) and not args.no_open:
        try:
            webbrowser.open("file://" + os.path.abspath(path))
        except Exception:
            pass

    print("=" * 64)
    return 0


def _keep_not_expired(t) -> bool:
    d = _parse_date(t.deadline)
    if not d:
        return True  # pas de date connue -> on garde par prudence
    return d >= date.today()


def _save_json(tenders: list):
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", f"marches-{date.today().isoformat()}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump([t.to_dict() for t in tenders], f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sys.exit(main())
