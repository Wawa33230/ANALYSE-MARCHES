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

from datetime import date, timedelta

from .base import http_post_json
from ..models import Tender

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
                buyer=_val(n.get("buyer-name")),
                market_type="Avis europeen (> seuils)",
                cpv=_as_list(n.get("classification-cpv")),
                publication_date=_val(n.get("publication-date"))[:10],
                deadline=_val(n.get("deadline-receipt-tender-date-lot"))[:10],
                url=NOTICE_URL.format(pub=pub) if pub else "https://ted.europa.eu/",
                description="",
            )
        )
    return tenders


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
