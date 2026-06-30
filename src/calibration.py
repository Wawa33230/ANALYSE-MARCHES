"""Outil de CALIBRAGE des filtres (base de donnees d'analyse, pas un tableau).

But : recuperer TOUS les marches publies par tes bailleurs clients sur 5 ans, puis
analyser leur vocabulaire reel (mots des objets, CPV, types de marche). Le resultat
sert a AFFINER les filtres du tableau de bord (config.yaml) pour qu'il fasse remonter
en priorite les vrais marches cibles.

Ce script NE produit PAS de tableau de recherche. Il genere un fichier d'analyse :
    data/calibration-bailleurs.json   (donnees structurees, a m'envoyer)
    output/calibration-bailleurs.txt  (resume lisible)

Lancement :
    python -m src.calibration               (5 ans)
    python -m src.calibration --annees 3
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import date

from .config import Config
from .scoring import normalize, _parse_date, as_text
from .sources.boamp import _build_search_clause, _fetch_where

# Mots vides (on les ignore dans l'analyse de vocabulaire)
STOP = set("""
de des du la le les un une et en pour sur par dans avec ou au aux a l d se sa son ses
ce cette ces nos vos leur leurs il elle est sont qui que quoi dont plus moins tout toute
n s y c m t marche marches lot lots prestation prestations travaux objet relatif relative
accord cadre bons commande commune ville mairie departement region cedex france
""".split())


def _tokens(text: str):
    text = normalize(text)
    words = re.findall(r"[a-z0-9][a-z0-9'-]{2,}", text)
    return [w for w in words if w not in STOP and not w.isdigit()]


def _bigrams(tokens):
    return [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]


# Heuristique "marche salle de bain" pour reperer le sous-ensemble cible
CIBLE_HINT = re.compile(
    r"baignoire|douche|salle de bain|salle d'eau|sanitaire|plomberie|pmr|accessibil|receveur|adaptation",
    re.IGNORECASE,
)


def analyser(config: Config, annees: int) -> dict:
    bailleurs = config.scoring.get("bailleurs_cibles", [])
    since = date(date.today().year - annees, date.today().month, 1).isoformat()
    date_clause = f' and dateparution >= "{since}"'

    par_bailleur = {}
    cpv_all, cpv_cible = Counter(), Counter()
    term_all, term_cible = Counter(), Counter()
    bigram_cible = Counter()
    types_all = Counter()
    n_total, n_cible = 0, 0

    for idx, root in enumerate(bailleurs, 1):
        rootn = normalize(root)
        print(f"  [{idx}/{len(bailleurs)}] {root} ...")
        try:
            where = _build_search_clause([root]) + date_clause
            avis = _fetch_where(where, max_records=1000)
        except Exception as e:  # noqa: BLE001
            par_bailleur[root] = {"erreur": str(e)}
            print(f"      /!\\ {e}")
            continue

        # On ne garde que les avis ou le nom du bailleur apparait vraiment
        avis = [a for a in avis if rootn in normalize(a.buyer)] or avis
        nb = len(avis)
        nb_cible = 0
        for a in avis:
            objet = as_text(a.title)
            toks = _tokens(objet)
            is_cible = bool(CIBLE_HINT.search(objet))
            n_total += 1
            if a.market_type:
                types_all[as_text(a.market_type)[:50]] += 1
            for c in (a.cpv or []):
                cpv_all[str(c)[:8]] += 1
                if is_cible:
                    cpv_cible[str(c)[:8]] += 1
            term_all.update(toks)
            if is_cible:
                nb_cible += 1
                n_cible += 1
                term_cible.update(toks)
                bigram_cible.update(_bigrams(toks))
        par_bailleur[root] = {"nb": nb, "nb_cible": nb_cible}

    return {
        "annees": annees,
        "n_total": n_total,
        "n_cible": n_cible,
        "par_bailleur": par_bailleur,
        "cpv_top_all": cpv_all.most_common(40),
        "cpv_top_cible": cpv_cible.most_common(40),
        "termes_top_cible": term_cible.most_common(80),
        "bigrammes_top_cible": bigram_cible.most_common(60),
        "termes_top_all": term_all.most_common(60),
        "types": types_all.most_common(15),
    }


def ecrire_resume(res: dict, path: str):
    L = []
    L.append("=" * 70)
    L.append(f" CALIBRAGE FILTRES - analyse {res['annees']} ans des bailleurs clients")
    L.append("=" * 70)
    L.append(f"Marches analyses : {res['n_total']}  |  dont 'salle de bain/plomberie' : {res['n_cible']}")
    L.append("")
    L.append("### CPV les plus frequents sur les marches CIBLES (a inclure dans config) :")
    for code, n in res["cpv_top_cible"]:
        L.append(f"   {code} : {n}")
    L.append("")
    L.append("### Mots les plus frequents sur les objets CIBLES (vocabulaire reel) :")
    L.append("   " + ", ".join(f"{w}({n})" for w, n in res["termes_top_cible"][:50]))
    L.append("")
    L.append("### Expressions (bigrammes) les plus frequentes sur objets CIBLES :")
    for w, n in res["bigrammes_top_cible"][:30]:
        L.append(f"   {w} : {n}")
    L.append("")
    L.append("### Types de marche utilises :")
    for t, n in res["types"]:
        L.append(f"   {t} : {n}")
    L.append("")
    L.append("### Activite par bailleur (nb total / dont cibles) :")
    for b, d in sorted(res["par_bailleur"].items(), key=lambda kv: -(kv[1].get("nb", 0))):
        if "erreur" in d:
            L.append(f"   {b} : (non recupere)")
        else:
            L.append(f"   {b} : {d['nb']} / {d['nb_cible']} cibles")
    text = "\n".join(L)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Calibrage des filtres a partir de l'historique bailleurs")
    parser.add_argument("--annees", type=int, default=5)
    args = parser.parse_args(argv)

    config = Config.load()
    print("=" * 60)
    print(f" CALIBRAGE - historique {args.annees} ans des bailleurs clients")
    print(" (recupere TOUS leurs marches, analyse CPV / mots / types)")
    print("=" * 60)
    res = analyser(config, args.annees)

    os.makedirs("data", exist_ok=True)
    with open("data/calibration-bailleurs.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    resume = ecrire_resume(res, "output/calibration-bailleurs.txt")
    print("\n" + resume)
    print("\n>> Fichiers generes :")
    print("   data/calibration-bailleurs.json   (a m'envoyer pour regler les filtres)")
    print("   output/calibration-bailleurs.txt  (resume lisible)")
    print("=" * 60)


if __name__ == "__main__":
    main()
