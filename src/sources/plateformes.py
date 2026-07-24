"""Connecteur "plateformes" - lecteur de flux RSS/Atom (methode universelle).

Les plateformes de dematerialisation (Ternum BFC, maximilien, achatpublic,
marches-securises, e-marchespublics, megalis, PLACE, etc.) sont majoritairement
rendues en JavaScript et/ou protegees : elles ne sont PAS scrapables en direct et
n'offrent pas d'API commune. La seule methode fiable et perenne pour TOUTES les
couvrir est de s'abonner au FLUX RSS de chaque recherche sauvegardee / alerte
(voir la section "plateformes" du config.yaml et le guide PLATEFORMES-RSS.md).

Ce connecteur lit chaque flux declare, en extrait les avis (titre, lien, date
limite si presente, acheteur si present) et les normalise. Il est defensif : un
flux invalide ou injoignable est simplement ignore (avertissement en console),
sans bloquer le reste de l'outil.

Chaque entree de `plateformes.flux_rss` peut etre :
  - une simple URL (chaine de caracteres), ou
  - un objet { url: ..., nom: "Ternum BFC", acheteur: "..." } pour etiqueter la
    source (et forcer un acheteur par defaut si le flux ne le fournit pas).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from .base import http_get
from ..models import Tender

DATE_RE = re.compile(r"(\d{4})[-/](\d{2})[-/](\d{2})")
# Reference du marche. Le \b initial/final evite les faux positifs comme le "no"
# a l'interieur de "baignoire" (n[°o] doit etre un mot isole, pas une sous-chaine).
REF_RE = re.compile(
    r"\b(?:r[ée]f[ée]rence|r[ée]f\.|n[°o]|consultation)\b\s*[:#\-]?\s*"
    r"([A-Za-z0-9][A-Za-z0-9\-_/.]{2,})",
    re.IGNORECASE,
)
# Acheteur mentionne dans le texte : "Acheteur : X", "Entite : X"... La capture
# non-gourmande s'arrete au 1er separateur (" - ", "|", ";", double espace) ou a
# une etiquette de champ suivante (date limite, reference...), pour ne pas deborder
# sur l'avis suivant quand tout le texte est sur une seule ligne.
BUYER_RE = re.compile(
    r"(?:acheteur|entit[ée]|organisme|pouvoir adjudicateur|donneur d'ordre|ma[îi]tre d'ouvrage)"
    r"\s*[:\-]\s*([^\n\r|;]+?)"
    r"(?=\s+-\s|\s{2,}|[|;]|$|\n|\r|\s*date\s+limite|\s*r[ée]f[ée]rence|\s*r[ée]f\.|"
    r"\s*consultation\b|\s*type\b|\s*proc[ée]dure\b)",
    re.IGNORECASE,
)


def _text(elem) -> str:
    return (elem.text or "").strip() if elem is not None else ""


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").strip()


def _guess_date(text: str) -> str:
    m = DATE_RE.search(text or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def _find(parent, localname):
    """Trouve un enfant en ignorant le namespace XML."""
    for child in parent:
        if child.tag.endswith("}" + localname) or child.tag == localname:
            return child
    return None


def _find_ns(parent, *localnames):
    """Cherche le premier enfant correspondant a l'un des noms (ns-insensible)."""
    for name in localnames:
        el = _find(parent, name)
        if el is not None:
            return el
    return None


def _extract_buyer(it, is_atom: bool, desc: str, default: str = "") -> str:
    # 1) champs structures : dc:creator, dc:publisher, author/name
    creator = _find_ns(it, "creator", "publisher")
    if creator is not None and _text(creator):
        return _text(creator)
    author = _find_ns(it, "author")
    if author is not None:
        name = _find_ns(author, "name")
        if name is not None and _text(name):
            return _text(name)
        if _text(author):
            return _text(author)
    # 2) motif dans la description
    m = BUYER_RE.search(desc or "")
    if m:
        return m.group(1).strip().rstrip(".,;:")
    return default


def _parse_feed(content: bytes, feed_url: str, label: str = "", default_buyer: str = "") -> list[Tender]:
    tenders: list[Tender] = []
    root = ET.fromstring(content)
    source_name = label or (urlparse(feed_url).netloc or "plateforme")

    items = root.findall(".//item")
    is_atom = False
    if not items:
        items = [e for e in root.iter() if e.tag.endswith("}entry") or e.tag == "entry"]
        is_atom = True

    for it in items:
        if is_atom:
            title = _text(_find(it, "title"))
            link_el = _find(it, "link")
            link = link_el.get("href") if link_el is not None else ""
            desc = _text(_find(it, "summary")) or _text(_find(it, "content"))
            pub = _text(_find(it, "updated")) or _text(_find(it, "published"))
        else:
            title = _text(it.find("title"))
            link = _text(it.find("link"))
            desc = _text(it.find("description"))
            pub = _text(it.find("pubDate"))

        desc = _strip_tags(desc)
        deadline = _guess_date(desc) or _guess_date(title)
        m = REF_RE.search(title) or REF_RE.search(desc)
        reference = m.group(1).rstrip(".,;:") if m else ""
        buyer = _extract_buyer(it, is_atom, desc, default_buyer)

        tenders.append(
            Tender(
                id=f"rss:{link or title}",
                source=source_name,
                title=title,
                reference=reference,
                buyer=buyer,
                market_type="Plateforme (flux RSS)",
                publication_date=_guess_date(pub),
                deadline=deadline,
                url=link,
                description=desc,
            )
        )
    return tenders


def _normalize_feeds(raw) -> list[dict]:
    """Accepte une liste d'URLs (str) ou d'objets {url, nom, acheteur}."""
    feeds: list[dict] = []
    for entry in raw or []:
        if isinstance(entry, str):
            url = entry.strip()
            if url and not url.startswith("#"):
                feeds.append({"url": url, "nom": "", "acheteur": ""})
        elif isinstance(entry, dict) and entry.get("url"):
            feeds.append(
                {
                    "url": str(entry["url"]).strip(),
                    "nom": str(entry.get("nom", "") or ""),
                    "acheteur": str(entry.get("acheteur", "") or ""),
                }
            )
    return feeds


def fetch(config) -> list[Tender]:
    feeds = _normalize_feeds(config.get("plateformes.flux_rss", []))
    if not feeds:
        print("    (i) Aucun flux RSS de plateforme configure "
              "(section 'plateformes' du config.yaml).")
        print("        -> Voir PLATEFORMES-RSS.md pour activer Ternum BFC, maximilien, achatpublic...")
        return []

    tenders: list[Tender] = []
    for f in feeds:
        label = f["nom"] or urlparse(f["url"]).netloc
        try:
            resp = http_get(
                f["url"],
                headers={"Accept": "application/rss+xml, application/atom+xml, application/xml, */*"},
            )
            found = _parse_feed(resp.content, f["url"], label=f["nom"], default_buyer=f["acheteur"])
            print(f"      {label} : {len(found)} avis (flux RSS).")
            tenders += found
        except Exception as e:  # noqa: BLE001
            print(f"    /!\\ Flux ignore ({label}) : {e}")
    return tenders
