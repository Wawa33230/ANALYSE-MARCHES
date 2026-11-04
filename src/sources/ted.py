"""Connecteur TED - Tenders Electronic Daily (Journal officiel de l'UE).

API de recherche publique v3 :
  https://api.ted.europa.eu/v3/notices/search

On cible les avis francais (FRA) recents avec un CPV plomberie/sanitaire.
Les gros accords-cadres au-dessus des seuils europeens y sont publies.

Remarque : l'API TED evolue regulierement. Le connecteur est volontairement
defensif : en cas d'erreur, il renvoie une liste vide sans bloquer le reste de
l'outil (un avertissement est affiche dans la console).
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from .base import http_post_json
from ..models import Tender

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

API = "https://api.ted.europa.eu/v3/notices/search"
NOTICE_URL = "https://ted.europa.eu/fr/notice/-/detail/{pub}"

# CPV cibles cote TED (plomberie, sanitaire, salles de bains, rehabilitation)
CPV = ["45330000", "45332400", "45211310", "45454000", "45453000"]


def _ft_terms(config) -> list[str]:
    """Mots-cles FORTS (>= 5 lettres) pour la recherche PLEIN TEXTE TED, derives de
    la config. Indispensable : beaucoup de marches d'ADAPTATION / ACCESSIBILITE sont
    classes par TED sous un CPV generique 'Travaux de construction' (hors de notre
    liste CPV plomberie) -> seuls les mots du titre permettent de les capter
    (cas Grand Delta Habitat : 'travaux d'adaptabilite des logements PMR')."""
    try:
        sc = config.scoring or {}
    except Exception:  # noqa: BLE001
        sc = {}
    base = list(sc.get("mots_cles_prioritaires", []) or [])
    out, seen = [], set()
    for t in base:
        t = (t or "").strip()
        if len(t) >= 5 and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    # Filet de securite : quelques termes cles toujours presents
    for t in ("adaptabilite", "mobilite reduite", "accessibilite",
              "salle de bain", "maintien a domicile", "adaptation"):
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:18]


def _payload(query: str) -> dict:
    return {
        "query": query,
        "fields": [
            "publication-number", "notice-title", "buyer-name",
            "classification-cpv", "publication-date",
            "deadline-receipt-tender-date-lot",
            "deadline-receipt-request-date-lot",
            "deadline-date-lot", "deadline", "links",
        ],
        "limit": 200,
        "scope": "ACTIVE",
        "paginationMode": "PAGE_NUMBER",
    }


def _run(query: str, label: str) -> list[dict]:
    """Execute une requete TED ; renvoie [] sans bloquer en cas d'erreur."""
    try:
        resp = http_post_json(API, _payload(query))
        data = resp.json()
        return data.get("notices", []) or data.get("results", []) or []
    except Exception as e:  # noqa: BLE001
        print(f"    /!\\ TED ({label}) : {e}")
        return []


def fetch(config) -> list[Tender]:
    jours = int(config.get("recherche.jours_recents", 45))
    since = (date.today() - timedelta(days=jours)).strftime("%Y%m%d")
    today = date.today().strftime("%Y%m%d")
    dates = f"publication-date>={since}<={today}"

    # 1) Requete par CPV plomberie/sanitaire (comportement historique, eprouve).
    cpv_clause = " OR ".join(f"classification-cpv={c}" for c in CPV)
    q_cpv = f"({cpv_clause}) AND buyer-country=FRA AND {dates}"

    # 2) Requete PLEIN TEXTE par mots-cles cible (capte les marches d'adaptation /
    #    accessibilite classes sous un CPV generique, hors liste CPV ci-dessus).
    ft_clause = " OR ".join(f'FT ~ "{t}"' for t in _ft_terms(config))
    q_ft = f"({ft_clause}) AND buyer-country=FRA AND {dates}"

    notices = _run(q_cpv, "CPV")
    seen_ids = {_val(n.get("publication-number")) for n in notices}
    for n in _run(q_ft, "mots-cles"):
        pid = _val(n.get("publication-number"))
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            notices.append(n)

    tenders: list[Tender] = []
    for n in notices:
        pub = _val(n.get("publication-number"))
        tenders.append(
            Tender(
                id=f"ted:{pub}",
                source="TED (UE)",
                title=_val(n.get("notice-title")),
                reference=pub,
                buyer=_val(n.get("buyer-name")),
                market_type="Avis europeen (> seuils)",
                cpv=_as_list(n.get("classification-cpv")),
                publication_date=_val(n.get("publication-date"))[:10],
                deadline=_find_deadline(n),
                url=NOTICE_URL.format(pub=pub) if pub else "https://ted.europa.eu/",
                description="",
            )
        )
    return tenders


def _collect_dates(node, under_deadline: bool, out: list):
    """Parcourt recursivement la structure d'un avis et collecte toutes les dates
    (AAAA-MM-JJ) trouvees sous une cle contenant 'deadline'."""
    if isinstance(node, dict):
        for k, v in node.items():
            kd = under_deadline or ("deadline" in str(k).lower())
            _collect_dates(v, kd, out)
    elif isinstance(node, list):
        for item in node:
            _collect_dates(item, under_deadline, out)
    elif under_deadline and isinstance(node, (str, int)):
        m = DATE_RE.search(str(node))
        if m:
            out.append(m.group(0))


def _find_deadline(notice: dict) -> str:
    """Date limite de l'avis TED, quelle que soit la forme exacte du champ.
    On prend la date la plus tardive trouvee (si plusieurs lots), pour ne pas
    masquer a tort un marche dont un lot est encore ouvert."""
    dates: list[str] = []
    _collect_dates(notice, False, dates)
    return max(dates) if dates else ""


def _val(v) -> str:
    """TED renvoie souvent des valeurs multilingues (dict) ou des listes."""
    if v is None:
        return ""
    if isinstance(v, dict):
        for lang in ("fra", "fr", "eng", "en"):
            if lang in v:
                return _val(v[lang])
        # premier element disponible
        for value in v.values():
            return _val(value)
        return ""
    if isinstance(v, list):
        return _val(v[0]) if v else ""
    return str(v)


def _as_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x)[:8] for x in v]
    return [str(v)[:8]]
