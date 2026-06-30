"""Connecteur BOAMP - Bulletin Officiel des Annonces des Marches Publics.

Utilise l'API ouverte Opendatasoft v2.1 (gratuite, sans cle) :
  https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records

C'est la source principale : la quasi-totalite des marches formalises de bailleurs
sociaux (accords-cadres, AO ouverts) y sont publies, y compris les marches du type
"France Loire" (plomberie / travaux d'accessibilite).
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from .base import http_get
from ..models import Tender

API = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"
AVIS_URL = "https://www.boamp.fr/pages/avis/?q=idweb:%22{idweb}%22"

# Limite Opendatasoft : 100 enregistrements par appel, offset max 10000.
PAGE_SIZE = 100


def _build_search_clause(keywords: list[str]) -> str:
    """Construit une clause ODSQL : search("kw1") or search("kw2") ..."""
    parts = []
    for kw in keywords:
        kw = kw.replace('"', "")
        parts.append(f'search("{kw}")')
    return "(" + " or ".join(parts) + ")"


def _extract_cpv(record: dict) -> list[str]:
    """Tente d'extraire les codes CPV depuis differents champs possibles."""
    codes: set[str] = set()
    # Champ structure "donnees" (JSON) present sur certains avis
    raw = record.get("donnees")
    if raw:
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            blob = json.dumps(data)
            import re

            for m in re.findall(r"\b(45\d{6}|50\d{6}|71\d{6})\b", blob):
                codes.add(m)
        except Exception:
            pass
    # Champs eventuels plus directs
    for key in ("code_cpv", "cpv", "code_cpv_facette"):
        v = record.get(key)
        if isinstance(v, str):
            codes.add(v[:8])
        elif isinstance(v, list):
            for item in v:
                codes.add(str(item)[:8])
    return [c for c in codes if c.isdigit()]


def _extract_reference(record: dict, idweb: str) -> str:
    """Reference du marche : on privilegie la reference de l'acheteur (ex '2026020'),
    sinon on retombe sur l'identifiant de l'avis BOAMP (toujours present)."""
    # 1) Champs directs eventuels
    for key in ("reference", "reference_marche", "num_marche", "nummarche"):
        v = record.get(key)
        if v:
            return str(v)
    # 2) Recherche dans le bloc structure "donnees"
    raw = record.get("donnees")
    if raw:
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw

            def _walk(node):
                if isinstance(node, dict):
                    for k, val in node.items():
                        if "reference" in str(k).lower() and isinstance(val, (str, int)) and str(val).strip():
                            return str(val).strip()
                        found = _walk(val)
                        if found:
                            return found
                elif isinstance(node, list):
                    for item in node:
                        found = _walk(item)
                        if found:
                            return found
                return None

            ref = _walk(data)
            if ref:
                return ref
        except Exception:
            pass
    # 3) Repli : identifiant de l'avis BOAMP
    return idweb


def _dept(record: dict) -> str:
    v = record.get("code_departement")
    if isinstance(v, list):
        return ", ".join(str(x) for x in v if x)
    return str(v) if v else ""


def _to_str(v) -> str:
    """Convertit n'importe quelle valeur BOAMP en texte (les champs peuvent etre des listes)."""
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(_to_str(x) for x in v if x not in (None, ""))
    if isinstance(v, dict):
        return ", ".join(_to_str(x) for x in v.values() if x not in (None, ""))
    return str(v)


def _first(record: dict, *keys, default=""):
    for k in keys:
        v = record.get(k)
        if v not in (None, "", []):
            return _to_str(v)
    return default


def _geo_clause(config) -> str:
    perimetre = config.get("geographie.perimetre", "national")
    depts = config.get("geographie.departements", []) or []
    if perimetre == "departements" and depts:
        dept_clause = " or ".join(f'code_departement = "{d}"' for d in depts)
        return f" and ({dept_clause})"
    return ""


def _map_record(rec: dict) -> Tender:
    idweb = str(_first(rec, "idweb", "id", default=""))
    return Tender(
        id=f"boamp:{idweb}",
        source="BOAMP",
        title=_first(rec, "objet", default=""),
        reference=_extract_reference(rec, idweb),
        buyer=_first(rec, "nomacheteur", "nom_acheteur", default=""),
        department=_dept(rec),
        market_type=_first(rec, "type_marche", "type_marche_facette", "nature", default=""),
        cpv=_extract_cpv(rec),
        publication_date=str(_first(rec, "dateparution", default="") or "")[:10],
        deadline=str(_first(rec, "datelimitereponse", "datelimite", default="") or "")[:10],
        url=AVIS_URL.format(idweb=idweb) if idweb else "https://www.boamp.fr/",
        description=_first(rec, "descripteur_libelle", "famille_libelle", default=""),
    )


def _fetch_where(where: str, max_records: int) -> list[Tender]:
    tenders: list[Tender] = []
    offset = 0
    while offset < max_records:
        params = {"where": where, "limit": PAGE_SIZE, "offset": offset, "order_by": "dateparution desc"}
        resp = http_get(API, params=params)
        results = resp.json().get("results", [])
        if not results:
            break
        tenders += [_map_record(r) for r in results]
        if len(results) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return tenders


def fetch(config) -> list[Tender]:
    scoring = config.scoring
    jours = config.get("recherche.jours_recents", 45)
    since = (date.today() - timedelta(days=int(jours))).isoformat()
    date_clause = f' and dateparution >= "{since}"'
    geo = _geo_clause(config)

    tenders: list[Tender] = []
    seen: set[str] = set()

    # Requete 1 : mots-cles "salle de bain" (rares, a fort signal) -> recuperes EN TOTALITE
    #             pour ne jamais tronquer un marche cible comme France Loire / Logiouest.
    prio_kw = scoring.get("mots_cles_prioritaires", [])
    if prio_kw:
        where1 = _build_search_clause(prio_kw) + date_clause + geo
        for t in _fetch_where(where1, max_records=3000):
            if t.id not in seen:
                seen.add(t.id)
                tenders.append(t)

    # Requete 2 : plomberie / sanitaire (plus large) -> plafonnee. Le scoring fera le tri
    #             (la construction et la grosse plomberie sont ensuite ecartees).
    sec_kw = [k for k in scoring.get("mots_cles_secondaires", []) if k.lower() != "entretien courant"]
    if sec_kw:
        where2 = _build_search_clause(sec_kw) + date_clause + geo
        for t in _fetch_where(where2, max_records=1000):
            if t.id not in seen:
                seen.add(t.id)
                tenders.append(t)

    # Requete 3 : par NOM DE BAILLEUR CONNU (clients de l'ex-apporteur). Sans filtre
    #             geographique : on veut TOUS leurs marches en cours, ou qu'ils soient.
    bailleurs = scoring.get("bailleurs_cibles", [])
    if bailleurs:
        # On decoupe en paquets de 25 pour ne pas faire une clause demesuree
        for i in range(0, len(bailleurs), 25):
            lot = bailleurs[i:i + 25]
            where3 = _build_search_clause(lot) + date_clause
            try:
                for t in _fetch_where(where3, max_records=600):
                    if t.id not in seen:
                        seen.add(t.id)
                        tenders.append(t)
            except Exception:
                continue

    return tenders
