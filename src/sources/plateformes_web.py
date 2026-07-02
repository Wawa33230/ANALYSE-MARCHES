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
import re
from html import unescape

import requests

from .base import HEADERS, TIMEOUT
from .marches_publics_info import _parse  # analyseur "par cartes" par defaut (AWS)
from ..models import Tender


def _txt(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html or ""))).strip()


# ---- Parseur dedie e-marchespublics.com (Dematis) : blocs <div class="box"> ----
_EMP_BOX = re.compile(r'<div class="box">(.*?)(?=<div class="box">|<div class="pagination|<footer|$)', re.DOTALL)
_EMP_OBJ = re.compile(r'class="texttruncate[^"]*"[^>]*>(.*?)</div>', re.DOTALL)
_EMP_BUYER = re.compile(r'class="box-body-top">\s*<span>(.*?)</span>', re.DOTALL)
_EMP_DL = re.compile(r"Date limite[^0-9]*(\d{2})/(\d{2})/(\d{4})", re.IGNORECASE | re.DOTALL)
_EMP_URL = re.compile(r'href=["\']?(/appel-offre/[^\s"\'#>]+)', re.IGNORECASE)
_EMP_CP = re.compile(r"\b(\d{5})\b")


def _parse_emp(html: str) -> list[Tender]:
    tenders: list[Tender] = []
    for block in _EMP_BOX.findall(html or ""):
        objm = _EMP_OBJ.search(block)
        objet = _txt(objm.group(1)) if objm else ""
        if len(objet) < 8:
            continue
        bm = _EMP_BUYER.search(block)
        buyer = _txt(bm.group(1)) if bm else ""
        dlm = _EMP_DL.search(block)
        deadline = f"{dlm.group(3)}-{dlm.group(2)}-{dlm.group(1)}" if dlm else ""
        um = _EMP_URL.search(block)
        url = "https://www.e-marchespublics.com" + um.group(1).split("#")[0] if um else "https://www.e-marchespublics.com/appel-offre"
        cpm = _EMP_CP.search(_txt(block))
        dept = cpm.group(1)[:2] if cpm else ""
        tenders.append(Tender(
            id=f"emp:{url}", source="e-marchespublics.com", title=objet,
            buyer=buyer, department=dept, market_type="Plateforme", deadline=deadline, url=url))
    return tenders


PARSEURS = {"cartes": _parse, "emp": _parse_emp}

# Mots-cles metier envoyes dans le champ de recherche de chaque plateforme.
QUERIES = [
    "adaptation PMR",
    "salle de bain accessibilite",
    "remplacement baignoire douche",
    "adaptation logement mobilite reduite",
]
MAX_PAGES = 8


def _raw(url: str, method: str, params: dict, encodage: str = ""):
    """Requete tolerante : renvoie le texte HTML meme si le statut est une erreur
    (utile pour capturer la page de diagnostic d'une plateforme non calibree)."""
    h = dict(HEADERS)
    h["Accept"] = "text/html,application/xhtml+xml"
    if method == "POST":
        resp = requests.post(url, data=params, headers=h, timeout=TIMEOUT)
    else:
        resp = requests.get(url, params=params, headers=h, timeout=TIMEOUT)
    if encodage:
        resp.encoding = encodage
    return resp.text or ""


def _fetch_platform(p: dict) -> list[Tender]:
    slug = p.get("slug", "plateforme")
    nom = p.get("nom", slug)
    url = p.get("url", "")
    method = str(p.get("methode", "GET")).upper()
    kw_field = p.get("champ_motcle", "q")
    page_field = p.get("champ_page", "page")
    calibre = bool(p.get("calibre", False))
    encodage = p.get("encodage", "")
    parseur = PARSEURS.get(p.get("parseur", "cartes"), _parse)
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
                html = _raw(url, method, params, encodage)
            except Exception as e:  # noqa: BLE001
                print(f"    /!\\ {nom} ({q}) : {e}")
                break
            if len(html) > len(debug_html):
                debug_html = html
            new = 0
            for t in parseur(html):
                if not t.source or t.source == "marches-publics.info (AWS)":
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
