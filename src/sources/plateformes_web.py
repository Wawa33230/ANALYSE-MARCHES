"""Connecteur GENERIQUE multi-plateformes (maximilien, achatpublic, marches-securises,
e-marchespublics, plateformes regionales...).

Chaque plateforme est decrite dans config.yaml (section "plateformes_web"). Ce
connecteur, pour chaque plateforme active :
  - interroge sa page de recherche (GET ou POST) avec tes mots-cles metier ;
  - tente d'extraire les annonces avec l'analyseur "par cartes" (comme AWS) ;
  - pagine tant que de nouvelles annonces arrivent ;
  - s'il ne reconnait rien, ENREGISTRE la page dans data/<slug>-debug.html pour
    calibrage (tu me l'envoies, je finalise le lecteur de cette plateforme).

Ainsi on ajoute les plateformes "une par une" : chaque nouvelle plateforme = une
entree de config + un tour de calibrage.
"""

from __future__ import annotations

import os

import requests

from .base import HEADERS, TIMEOUT
from .marches_publics_info import _parse  # analyseur "par cartes" par defaut
from ..models import Tender

# Mots-cles metier envoyes dans le champ de recherche de chaque plateforme.
QUERIES = [
    "adaptation PMR",
    "salle de bain accessibilite",
    "remplacement baignoire douche",
    "adaptation logement mobilite reduite",
]
MAX_PAGES = 8


def _raw(url: str, method: str, params: dict):
    """Requete tolerante : renvoie le texte HTML meme si le statut est une erreur
    (utile pour capturer la page de diagnostic d'une plateforme non calibree)."""
    h = dict(HEADERS)
    h["Accept"] = "text/html,application/xhtml+xml"
    if method == "POST":
        resp = requests.post(url, data=params, headers=h, timeout=TIMEOUT)
    else:
        resp = requests.get(url, params=params, headers=h, timeout=TIMEOUT)
    return resp.text or ""


def _fetch_platform(p: dict) -> list[Tender]:
    slug = p.get("slug", "plateforme")
    nom = p.get("nom", slug)
    url = p.get("url", "")
    method = str(p.get("methode", "GET")).upper()
    kw_field = p.get("champ_motcle", "q")
    page_field = p.get("champ_page", "page")
    calibre = bool(p.get("calibre", False))
    if not url:
        return []

    # Plateforme non calibree : une seule requete-sonde pour recuperer le HTML.
    queries = QUERIES if calibre else QUERIES[:1]
    max_pages = MAX_PAGES if calibre else 1

    tenders: list[Tender] = []
    seen: set[str] = set()
    debug_html = ""

    for q in queries:
        for page in range(1, max_pages + 1):
            params = {kw_field: q, page_field: page}
            # champs supplementaires eventuels definis en config
            params.update(p.get("champs_fixes", {}) or {})
            try:
                html = _raw(url, method, params)
            except Exception as e:  # noqa: BLE001
                print(f"    /!\\ {nom} ({q}) : {e}")
                break
            if len(html) > len(debug_html):
                debug_html = html
            new = 0
            for t in _parse(html):
                t.source = nom
                t.id = f"{slug}:{t.reference or t.url or t.title[:40]}"
                if t.id not in seen:
                    seen.add(t.id)
                    tenders.append(t)
                    new += 1
            if new == 0:
                break

    if not tenders:
        try:
            os.makedirs("data", exist_ok=True)
            path = os.path.join("data", f"{slug}-debug.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(debug_html or f"(aucune reponse de {url})")
            print(f"    (i) {nom} : non calibre. Page enregistree dans "
                  f"data\\{slug}-debug.html -> envoie ce fichier pour l'activer.")
        except Exception:
            pass
    else:
        print(f"    {nom} : {len(tenders)} annonce(s).")
    return tenders


def fetch(config) -> list[Tender]:
    platforms = config.get("plateformes_web", []) or []
    tenders: list[Tender] = []
    for p in platforms:
        if not p.get("actif", False):
            continue
        try:
            tenders += _fetch_platform(p)
        except Exception as e:  # noqa: BLE001
            print(f"    /!\\ {p.get('nom', p.get('slug', '?'))} : {e}")
    return tenders
