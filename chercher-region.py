"""Recherche ad-hoc de marches sur le BOAMP, par departement(s).

Pratique pour retrouver un marche precis dont on connait la zone (ex : "un gros
marche de 18 lots du cote de Marseille ou Toulon"). Liste les avis recents des
departements demandes, TRIES PAR NOMBRE DE LOTS decroissant, avec le lien BOAMP.

Usage (dans une fenetre cmd, depuis le dossier de l'outil) :
    python chercher-region.py              (par defaut : 13 et 83 = Marseille / Toulon)
    python chercher-region.py 13 83 06     (autres departements)
    python chercher-region.py 44 --jours 180

Aucune cle requise : l'API BOAMP (Opendatasoft) est publique et gratuite.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, timedelta

import requests

API = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"
AVIS = "https://www.boamp.fr/pages/avis/?q=idweb:%22{}%22"


def _args():
    depts, jours = [], 120
    it = iter(sys.argv[1:])
    for a in it:
        if a in ("--jours", "-j"):
            jours = int(next(it, 120))
        elif a.isdigit():
            depts.append(a)
    return (depts or ["13", "83"]), jours


def _lots(rec: dict) -> int:
    """Estime le nombre de lots : on cherche '<n> lots' dans l'objet et les donnees."""
    raw = rec.get("donnees")
    try:
        blob = json.dumps(json.loads(raw) if isinstance(raw, str) else raw, ensure_ascii=False)
    except Exception:
        blob = str(raw or "")
    txt = (rec.get("objet") or "") + " " + blob
    nums = [int(n) for n in re.findall(r"(\d{1,3})\s*lots?\b", txt, re.I)]
    return max(nums) if nums else 0


def main():
    depts, jours = _args()
    since = (date.today() - timedelta(days=jours)).isoformat()
    dept_clause = " or ".join(f'code_departement="{d}"' for d in depts)
    where = f'({dept_clause}) and dateparution >= "{since}"'

    rows, offset = [], 0
    while offset < 2000:
        params = {"where": where, "limit": 100, "offset": offset, "order_by": "dateparution desc"}
        r = requests.get(API, params=params, timeout=40)
        r.raise_for_status()
        res = r.json().get("results", [])
        if not res:
            break
        rows += res
        if len(res) < 100:
            break
        offset += 100

    print(f"\n{len(rows)} avis - departements {depts} - publies depuis {since}")
    print("(tries par nombre de lots decroissant - ton gros marche doit etre en haut)\n")
    print("=" * 100)
    for rec in sorted(rows, key=lambda r: -_lots(r)):
        n = _lots(rec)
        obj = (rec.get("objet") or "").replace("\n", " ").strip()[:140]
        ach = str(rec.get("nomacheteur") or rec.get("nom_acheteur") or "")[:45]
        dep = rec.get("code_departement")
        dlr = str(rec.get("datelimitereponse") or rec.get("datelimite") or "")[:10]
        idw = rec.get("idweb") or rec.get("id")
        tag = f"[{n:>2} lots]" if n else "[  ?    ]"
        print(f"{tag} [{dep}] {ach}")
        print(f"          {obj}")
        print(f"          limite {dlr}  |  {AVIS.format(idw)}")
        print("-" * 100)


if __name__ == "__main__":
    main()
