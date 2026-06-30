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
CPV = ["45330000", "45332400", "45211310", "45454000"]


def fetch(config) -> list[Tender]:
    jours = int(config.get("recherche.jours_recents", 45))
    since = (date.today() - timedelta(days=jours)).strftime("%Y%m%d")
    today = date.today().strftime("%Y%m%d")

    cpv_clause = " OR ".join(f"classification-cpv={c}" for c in CPV)
    query = (
        f"({cpv_clause}) "
        f"AND buyer-country=FRA "
        f"AND publication-date>={since}<={today}"
    )

    payload = {
        "query": query,
        "fields": [
            "publication-number",
            "notice-title",
            "buyer-name",
            "classification-cpv",
            "publication-date",
            "deadline-receipt-tender-date-lot",
            "deadline-receipt-request-date-lot",
            "deadline-date-lot",
            "deadline",
            "links",
        ],
        "limit": 100,
        "scope": "ACTIVE",
        "paginationMode": "PAGE_NUMBER",
    }

    resp = http_post_json(API, payload)
    data = resp.json()
    notices = data.get("notices", []) or data.get("results", [])

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
