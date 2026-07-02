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

# Analyse par "cartes" : chaque annonce commence par "Publie le ..." sur le site AWS.
CARD_SPLIT = re.compile(r"Publi[ée]\s+le", re.IGNORECASE)
PUB_RE = re.compile(r"Publi[ée]\s+le\s*:?\s*(\d{2})/(\d{2})/(\d{2,4})", re.IGNORECASE)
DL_RE = re.compile(r"Date\s+limite\s*:?\s*(?:le\s+)?(\d{2})/(\d{2})/(\d{2,4})", re.IGNORECASE)
REF_RE = re.compile(r"r[ée]f\.?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-/_.]{3,})", re.IGNORECASE)
HREF_RE = re.compile(r'href="([^"]+)"', re.IGNORECASE)
# Nom d'acheteur souvent suivi d'un code entre parentheses, ex "OPAC SAVOIE (73024)"
BUYER_RE = re.compile(r"([A-ZÉÈÀÂÎÔÛÇ][A-Za-zÉÈÀÂÎÔÛÇ'&\-\. ]{4,60})\s*\((\d{4,6})\)")

# Fallback : anciens liens directs vers une consultation
LINK_RE = re.compile(
    r'<a[^>]+href="([^"]*(?:onsultation|onsulter|Detail|idMarche|annonce)[^"]*)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


def _clean(html: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", html or "")).replace("\xa0", " ").strip()


def _abs(url: str) -> str:
    if url.startswith("http"):
        return url
    return BASE + ("" if url.startswith("/") else "/") + url


def _iso(d, m, y) -> str:
    y = ("20" + y) if len(y) == 2 else y
    return f"{y}-{m}-{d}"


def _parse(html: str) -> list[Tender]:
    """Analyse la page de resultats AWS par 'cartes' (une par 'Publie le ...')."""
    html = unescape(html or "")
    tenders: list[Tender] = []
    seen: set[str] = set()

    segments = CARD_SPLIT.split(html)
    for seg in segments[1:]:
        card_html = "Publie le" + seg
        # On coupe la carte au debut de la suivante (deja fait par split) ; on borne
        # aussi sur les actions de fin de carte pour ne pas deborder.
        text = _clean(card_html)

        dl = DL_RE.search(text)
        deadline = _iso(*dl.groups()) if dl else ""
        pub = PUB_RE.search(text)
        publication = _iso(*pub.groups()) if pub else ""
        refm = REF_RE.search(text)
        reference = refm.group(1).rstrip(".,;:") if refm else ""
        buyerm = BUYER_RE.search(text)
        buyer = (buyerm.group(1).strip() + f" ({buyerm.group(2)})") if buyerm else ""

        # Objet : ce qui suit la reference (ou l'acheteur), tronque avant les boutons
        objet = ""
        if refm:
            objet = text[refm.end():]
        elif buyerm:
            objet = text[buyerm.end():]
        for stop in ("Consulter l'avis", "Consulter", "Contacter", "Deposer", "Marche alloti", "DCE"):
            i = objet.find(stop)
            if i > 20:
                objet = objet[:i]
        objet = objet.strip(" -[]").strip()
        if len(objet) < 12:
            continue

        href = HREF_RE.search(card_html)
        url = _abs(href.group(1)) if href else SEARCH_URL
        key = reference or url or objet[:40]
        if key in seen:
            continue
        seen.add(key)

        tenders.append(
            Tender(
                id=f"aws:{key}",
                source="marches-publics.info (AWS)",
                title=objet,
                reference=reference,
                buyer=buyer,
                market_type="Plateforme AWS",
                publication_date=publication,
                deadline=deadline,
                url=url,
            )
        )

    # Fallback ancien format (liens directs) si le decoupage par cartes n'a rien donne
    if not tenders:
        for href, label in LINK_RE.findall(html):
            title = _clean(label)
            if len(title) < 12:
                continue
            url = _abs(href)
            if url in seen:
                continue
            seen.add(url)
            tenders.append(Tender(id=f"aws:{url}", source="marches-publics.info (AWS)",
                                  title=title, market_type="Plateforme AWS", url=url))
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
