"""Connecteur AWS - marches-publics.info (plateforme AWS-Achat).

AWS ne fournit pas de flux public officiel pour les outils tiers. On s'appuie donc
sur leur PAGE DE RECHERCHE PUBLIQUE (consultations en cours), que l'on interroge par
mots-cles et dont on analyse le HTML.

IMPORTANT : la structure exacte de cette page n'a pas pu etre verifiee depuis
l'environnement de developpement. Ce connecteur est donc DEFENSIF :
  - il essaie plusieurs formes de requete ;
  - s'il ne reconnait rien, il enregistre la page recue dans data/aws-debug.html
    (pour calibrage) et renvoie une liste vide sans bloquer le reste de l'outil.

Si tu obtiens 0 resultat AWS : envoie le fichier data/aws-debug.html, il permet
d'ajuster l'analyse en quelques minutes.
"""

from __future__ import annotations

import os
import re
from html import unescape

from .base import http_get
from ..models import Tender

SEARCH_URL = "https://www.marches-publics.info/Annonces/rechercher"
BASE = "https://www.marches-publics.info"

# Requetes ciblees sur ton metier (renovation de salle de bain)
QUERIES = [
    "accessibilite plomberie",
    "adaptation salle de bain",
    "remplacement baignoire douche",
    "douche PMR",
    "plomberie sanitaire entretien",
]

# Noms de parametres possibles pour le champ "mots-cles" (on les tente tous)
PARAM_CANDIDATES = ["texte", "motscles", "mots_cles", "q", "recherche", "keyword"]

# Liens vers une consultation : on tente plusieurs motifs rencontres sur AWS
LINK_RE = re.compile(
    r'<a[^>]+href="([^"]*(?:onsultation|onsulter|Detail|idMarche|aff_consultation|annonce)[^"]*)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
DATE_RE = re.compile(r"(\d{2})[/-](\d{2})[/-](\d{4})")
REF_RE = re.compile(r"(?:r[ée]f[ée]rence|r[ée]f\.?|consultation)\s*[:\-]?\s*([A-Za-z0-9][\w\-/.]{2,})", re.IGNORECASE)


def _clean(html: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", html or "")).strip()


def _abs(url: str) -> str:
    if url.startswith("http"):
        return url
    return BASE + ("" if url.startswith("/") else "/") + url


def _parse(html: str) -> list[Tender]:
    tenders: list[Tender] = []
    seen: set[str] = set()
    for href, label in LINK_RE.findall(html):
        title = _clean(label)
        if len(title) < 12:  # ignore les liens trop courts (menus, boutons)
            continue
        url = _abs(href)
        if url in seen:
            continue
        seen.add(url)
        m = DATE_RE.search(title)
        deadline = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""
        rm = REF_RE.search(title)
        tenders.append(
            Tender(
                id=f"aws:{url}",
                source="marches-publics.info (AWS)",
                title=title,
                reference=rm.group(1).rstrip(".,;:") if rm else "",
                market_type="Plateforme AWS",
                deadline=deadline,
                url=url,
            )
        )
    return tenders


def _try_fetch(query: str):
    """Tente la requete avec differents noms de parametre ; renvoie (html, params_ok)."""
    last_html = ""
    for param in PARAM_CANDIDATES:
        try:
            resp = http_get(SEARCH_URL, params={param: query},
                            headers={"Accept": "text/html,application/xhtml+xml"})
            last_html = resp.text
            if _parse(last_html):
                return last_html, True
        except Exception:
            continue
    return last_html, False


def fetch(config) -> list[Tender]:
    tenders: list[Tender] = []
    seen: set[str] = set()
    debug_html = ""
    any_parsed = False

    for q in QUERIES:
        html, ok = _try_fetch(q)
        if html and not debug_html:
            debug_html = html
        if ok:
            any_parsed = True
            for t in _parse(html):
                if t.id not in seen:
                    seen.add(t.id)
                    tenders.append(t)

    if not any_parsed:
        # On enregistre la page pour calibrage et on previent gentiment
        try:
            os.makedirs("data", exist_ok=True)
            with open(os.path.join("data", "aws-debug.html"), "w", encoding="utf-8") as f:
                f.write(debug_html or "(aucune reponse recue de marches-publics.info)")
            print("    (i) AWS : aucune annonce reconnue automatiquement. La page a ete")
            print("        enregistree dans data\\aws-debug.html -> envoie ce fichier pour calibrage.")
        except Exception:
            pass

    return tenders
