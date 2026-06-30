"""Connecteur "plateformes" - lecteur de flux RSS/Atom.

Les plateformes de dematerialisation (marches-publics.info / AWS, achatpublic.com,
marches-securises.fr, etc.) ne proposent pas d'API publique stable. La methode
fiable et perenne consiste a s'appuyer sur les FLUX RSS de tes recherches
sauvegardees / alertes (voir la section "plateformes" du config.yaml et le README).

Ce connecteur lit chaque flux declare, en extrait les avis, et les normalise.
Il est defensif : un flux invalide ou injoignable est simplement ignore (avec un
avertissement en console), sans bloquer le reste de l'outil.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from .base import http_get
from ..models import Tender

DATE_RE = re.compile(r"(\d{4})[-/](\d{2})[-/](\d{2})")
# Reference type "Reference : XXXX", "Ref. XXXX", "n° XXXX", "consultation XXXX"
REF_RE = re.compile(
    r"(?:r[ée]f[ée]rence|r[ée]f\.?|n[°o]|consultation)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-_/.]{2,})",
    re.IGNORECASE,
)


def _text(elem) -> str:
    return (elem.text or "").strip() if elem is not None else ""


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").strip()


def _guess_deadline(text: str) -> str:
    """Cherche une date type AAAA-MM-JJ dans le texte de l'avis (best-effort)."""
    m = DATE_RE.search(text or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def _parse_feed(content: bytes, feed_url: str) -> list[Tender]:
    tenders: list[Tender] = []
    root = ET.fromstring(content)
    source_name = urlparse(feed_url).netloc or "plateforme"

    # RSS 2.0 : channel/item ;  Atom : feed/entry
    items = root.findall(".//item")
    is_atom = False
    if not items:
        # gestion des namespaces Atom
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
        deadline = _guess_deadline(desc) or _guess_deadline(title)
        m = REF_RE.search(title) or REF_RE.search(desc)
        reference = m.group(1).rstrip(".,;:") if m else ""
        tenders.append(
            Tender(
                id=f"rss:{link or title}",
                source=source_name,
                title=title,
                reference=reference,
                buyer="",
                market_type="Plateforme (flux)",
                publication_date=_guess_deadline(pub),
                deadline=deadline,
                url=link,
                description=desc,
            )
        )
    return tenders


def _find(parent, localname):
    """Trouve un enfant en ignorant le namespace XML."""
    for child in parent:
        if child.tag.endswith("}" + localname) or child.tag == localname:
            return child
    return None


def fetch(config) -> list[Tender]:
    feeds = config.get("plateformes.flux_rss", []) or []
    if not feeds:
        print("    (i) Aucun flux RSS de plateforme configure "
              "(section 'plateformes' du config.yaml). Etape facultative.")
        return []

    tenders: list[Tender] = []
    for url in feeds:
        try:
            resp = http_get(url, headers={"Accept": "application/rss+xml, application/atom+xml, */*"})
            tenders += _parse_feed(resp.content, url)
        except Exception as e:  # noqa: BLE001
            print(f"    /!\\ Flux ignore ({url}) : {e}")
    return tenders
